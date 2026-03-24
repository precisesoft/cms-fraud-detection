"""Tests for retrospective validation logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call, mock_open, patch

import polars as pl
import pytest

from src.scoring.score import ScoreCard
from src.scoring.taxonomy import CaseLabel
from src.validation.retrospective import (
    blind_score_row,
    load_cases,
    main,
    original_score_row,
    run_validation,
)


def _revoked_case(**overrides: object) -> dict:
    """A revoked provider with outlier billing patterns."""
    row: dict = {
        "npi": "1234567890",
        "present_in_2025_enrollment_file": 1,
        "present_in_2026_revocation_file": 1,
        "medicare_participating_ind": "Y",
        "peer_case_count": 30,
        "service_volume_peer_z": 4.0,
        "services_per_bene_peer_z": 3.5,
        "submitted_to_allowed_peer_z": 0.5,
        "payment_peer_z": 0.5,
        "peer_avg_tot_srvcs": 150.0,
        "provider_total_benes": 200.0,
    }
    row.update(overrides)
    return row


class TestBlindScoring:
    def test_blind_removes_revocation_risk(self):
        row = _revoked_case()
        original = original_score_row(row)
        blind = blind_score_row(row)
        # Blind score should have LESS risk (no +25 revocation)
        assert blind["blind_risk"] < original["original_risk"]

    def test_blind_adds_no_revocation_legitimacy(self):
        row = _revoked_case()
        original = original_score_row(row)
        blind = blind_score_row(row)
        # Blind score should have MORE legitimacy (gains +15 no_revocation)
        assert blind["blind_legitimacy"] > original["original_legitimacy"]

    def test_outlier_still_detected_blind(self):
        """Provider with extreme z-scores should still be flagged even blind."""
        row = _revoked_case(
            service_volume_peer_z=6.0,
            services_per_bene_peer_z=6.0,
            submitted_to_allowed_peer_z=6.0,
            payment_peer_z=6.0,
            provider_total_benes=30.0,
            medicare_participating_ind="N",
            present_in_2025_enrollment_file=0,
        )
        blind = blind_score_row(row)
        # Extreme outlier should still flag as high_risk or review
        assert blind["blind_label"] in ("high_risk", "review")

    def test_normal_revoked_becomes_stable_blind(self):
        """Provider with normal billing but revoked should become stable blind."""
        row = _revoked_case(
            service_volume_peer_z=0.3,
            services_per_bene_peer_z=0.2,
            submitted_to_allowed_peer_z=0.1,
            payment_peer_z=0.1,
        )
        blind = blind_score_row(row)
        # Normal billing patterns → stable when revocation removed
        assert blind["blind_label"] == "stable"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scorecard(risk: int = 30, legitimacy: int = 60, label: str = "stable") -> ScoreCard:
    """Build a minimal ScoreCard suitable for mocking score_case returns."""
    return ScoreCard(
        risk_score=risk,
        legitimacy_score=legitimacy,
        case_label=CaseLabel(label),
        signals=(),
    )


def _make_dataframe(
    *,
    n_revoked: int = 2,
    n_non_revoked: int = 1,
) -> pl.DataFrame:
    """Build a minimal synthetic DataFrame for load_cases / run_validation tests."""
    base_row = {
        "npi": "1111111111",
        "hcpcs_cd": "99213",
        "present_in_2026_revocation_file": 1,
        "revocation_reason_summary": "False claims",
        "present_in_2025_enrollment_file": 0,
        "medicare_participating_ind": "N",
        "peer_case_count": 30,
        "service_volume_peer_z": 4.0,
        "services_per_bene_peer_z": 3.5,
        "submitted_to_allowed_peer_z": 0.5,
        "payment_peer_z": 0.5,
        "peer_avg_tot_srvcs": 150.0,
        "provider_total_benes": 200.0,
    }

    revoked_rows = []
    for i in range(n_revoked):
        r = dict(base_row)
        r["npi"] = str(1000000000 + i)
        r["present_in_2026_revocation_file"] = 1
        revoked_rows.append(r)

    non_revoked_rows = []
    for i in range(n_non_revoked):
        r = dict(base_row)
        r["npi"] = str(2000000000 + i)
        r["present_in_2026_revocation_file"] = 0
        r["revocation_reason_summary"] = None
        non_revoked_rows.append(r)

    all_rows = revoked_rows + non_revoked_rows
    return pl.DataFrame(all_rows)


# ---------------------------------------------------------------------------
# TestLoadCases
# ---------------------------------------------------------------------------

class TestLoadCases:
    def test_load_cases_calls_polars_read_csv(self, tmp_path: Path):
        """load_cases delegates to pl.read_csv with the supplied path."""
        # Write a minimal CSV that polars can actually parse
        csv = tmp_path / "cases.csv"
        csv.write_text(
            "npi,present_in_2026_revocation_file\n"
            "1234567890,1\n"
        )
        df = load_cases(csv)
        assert isinstance(df, pl.DataFrame)
        assert df.shape[0] == 1
        assert "npi" in df.columns

    def test_load_cases_mocked_read_csv(self):
        """load_cases passes the path + kwargs to pl.read_csv and returns its result."""
        fake_df = pl.DataFrame({"npi": ["9999999999"]})
        with patch("src.validation.retrospective.pl.read_csv", return_value=fake_df) as mock_csv:
            result = load_cases(Path("/fake/path.csv"))
        mock_csv.assert_called_once_with(
            Path("/fake/path.csv"),
            infer_schema_length=5000,
            null_values=["", "NA", "NULL"],
        )
        assert result is fake_df


# ---------------------------------------------------------------------------
# TestRunValidation
# ---------------------------------------------------------------------------

class TestRunValidation:
    """Tests for run_validation() end-to-end pipeline."""

    def _patch_load_and_score(self, fake_df: pl.DataFrame, score_returns: list[ScoreCard]):
        """Return a context-manager tuple: patch load_cases + patch score_case."""
        load_patch = patch(
            "src.validation.retrospective.load_cases", return_value=fake_df
        )
        score_patch = patch(
            "src.validation.retrospective.score_case", side_effect=score_returns
        )
        return load_patch, score_patch

    def test_returns_dict_with_expected_keys(self):
        """run_validation returns a dict with required top-level keys."""
        df = _make_dataframe(n_revoked=1, n_non_revoked=1)
        # Calls: 1 revoked blind + 1 revoked original + 1 non-revoked label +
        #        1 non-revoked risk sample = 4 score_case calls
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        sc_stable = _make_scorecard(risk=10, legitimacy=80, label="stable")
        score_returns = [sc_high, sc_stable, sc_stable, sc_stable]

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert set(result.keys()) == {
            "summary",
            "case_level",
            "provider_level",
            "non_revoked_baseline",
            "by_revocation_reason",
        }

    def test_summary_fields_present(self):
        """run_validation['summary'] contains all required numeric keys."""
        df = _make_dataframe(n_revoked=1, n_non_revoked=1)
        sc = _make_scorecard(risk=60, legitimacy=20, label="high_risk")
        score_returns = [sc] * 10

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        s = result["summary"]
        for key in (
            "total_revoked_cases",
            "total_revoked_npis",
            "case_detection_rate",
            "npi_detection_rate",
            "avg_blind_risk_score_revoked",
            "avg_risk_score_non_revoked",
            "risk_score_lift",
        ):
            assert key in s, f"Missing summary key: {key}"

    def test_detection_rate_high_risk(self):
        """All-high-risk blind labels → case_detection_rate == 1.0."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=1)
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        sc_stable = _make_scorecard(risk=10, legitimacy=80, label="stable")
        # For 2 revoked rows: blind_score (high_risk) + original_score each
        # + 1 non-revoked label + 1 non-revoked risk sample
        score_returns = [sc_high, sc_stable] * 2 + [sc_stable] * 4

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert result["summary"]["case_detection_rate"] == 1.0

    def test_detection_rate_all_stable(self):
        """All-stable blind labels → case_detection_rate == 0.0."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=1)
        sc_stable = _make_scorecard(risk=10, legitimacy=80, label="stable")
        score_returns = [sc_stable] * 20

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert result["summary"]["case_detection_rate"] == 0.0

    def test_zero_revoked_rows(self):
        """run_validation handles a DataFrame with no revoked rows gracefully."""
        df = _make_dataframe(n_revoked=0, n_non_revoked=2)
        sc_stable = _make_scorecard()
        score_returns = [sc_stable] * 10

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert result["summary"]["total_revoked_cases"] == 0
        assert result["summary"]["total_revoked_npis"] == 0
        assert result["summary"]["case_detection_rate"] == 0
        assert result["summary"]["npi_detection_rate"] == 0

    def test_zero_non_revoked_rows(self):
        """run_validation handles a DataFrame with no non-revoked rows gracefully."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=0)
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        score_returns = [sc_high] * 10

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert result["summary"]["avg_risk_score_non_revoked"] == 0

    def test_npi_level_aggregation_worst_case(self):
        """Two case rows for the same NPI: worst label wins at provider level."""
        # Build a DF where two rows share the same NPI, both revoked
        row_base = {
            "npi": "1111111111",
            "hcpcs_cd": "99213",
            "present_in_2026_revocation_file": 1,
            "revocation_reason_summary": "False claims",
            "present_in_2025_enrollment_file": 0,
            "medicare_participating_ind": "N",
            "peer_case_count": 30,
            "service_volume_peer_z": 4.0,
            "services_per_bene_peer_z": 3.5,
            "submitted_to_allowed_peer_z": 0.5,
            "payment_peer_z": 0.5,
            "peer_avg_tot_srvcs": 150.0,
            "provider_total_benes": 200.0,
        }
        row2 = dict(row_base)
        row2["hcpcs_cd"] = "99214"
        df = pl.DataFrame([row_base, row2])

        # Row 1: blind=stable, original=high_risk
        # Row 2: blind=high_risk, original=high_risk
        sc_stable = _make_scorecard(risk=10, legitimacy=80, label="stable")
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        # Order: blind_row1, original_row1, blind_row2, original_row2, (no non-revoked)
        score_returns = [sc_stable, sc_high, sc_high, sc_high]

        load_p = patch("src.validation.retrospective.load_cases", return_value=df)
        score_p = patch(
            "src.validation.retrospective.score_case", side_effect=score_returns
        )
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        # Only 1 unique NPI, worst label should be high_risk
        assert result["summary"]["total_revoked_npis"] == 1
        assert result["provider_level"]["blind_labels"].get("high_risk", 0) == 1

    def test_reason_stratification(self):
        """by_revocation_reason groups results by revocation_reason_summary."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=0)
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        score_returns = [sc_high] * 10

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        # Both revoked rows have reason "False claims"
        assert "False claims" in result["by_revocation_reason"]
        reason_data = result["by_revocation_reason"]["False claims"]
        assert "total" in reason_data
        assert "detection_rate" in reason_data

    def test_reason_stratification_null_reason(self):
        """Rows with a null revocation_reason_summary are bucketed as 'unknown'."""
        row = {
            "npi": "9999999999",
            "hcpcs_cd": "99213",
            "present_in_2026_revocation_file": 1,
            "revocation_reason_summary": None,
            "present_in_2025_enrollment_file": 0,
            "medicare_participating_ind": "N",
            "peer_case_count": 30,
            "service_volume_peer_z": 4.0,
            "services_per_bene_peer_z": 3.5,
            "submitted_to_allowed_peer_z": 0.5,
            "payment_peer_z": 0.5,
            "peer_avg_tot_srvcs": 150.0,
            "provider_total_benes": 200.0,
        }
        df = pl.DataFrame([row])
        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        score_returns = [sc_high] * 10

        load_p = patch("src.validation.retrospective.load_cases", return_value=df)
        score_p = patch(
            "src.validation.retrospective.score_case", side_effect=score_returns
        )
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert "unknown" in result["by_revocation_reason"]

    def test_blind_risk_distribution_avg(self):
        """avg_blind_risk_score_revoked equals the mean of blind ScoreCard risk scores."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=0)
        sc_a = _make_scorecard(risk=40, legitimacy=20, label="review")
        sc_b = _make_scorecard(risk=60, legitimacy=10, label="high_risk")
        sc_orig = _make_scorecard(risk=80, legitimacy=5, label="high_risk")
        # 2 revoked rows → blind_a, orig_a, blind_b, orig_b
        score_returns = [sc_a, sc_orig, sc_b, sc_orig]

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        expected_avg = round((40 + 60) / 2, 1)
        assert result["summary"]["avg_blind_risk_score_revoked"] == expected_avg

    def test_review_label_counts_as_detected(self):
        """'review' blind labels are counted in the detection rate."""
        df = _make_dataframe(n_revoked=2, n_non_revoked=0)
        sc_review = _make_scorecard(risk=40, legitimacy=30, label="review")
        sc_orig = _make_scorecard(risk=80, legitimacy=5, label="high_risk")
        score_returns = [sc_review, sc_orig] * 2

        load_p, score_p = self._patch_load_and_score(df, score_returns)
        with load_p, score_p:
            result = run_validation(Path("/fake/demo.csv"))

        assert result["summary"]["case_detection_rate"] == 1.0

    def test_non_revoked_sample_cap(self):
        """Non-revoked rows beyond 2000 are not scored for the risk sample."""
        # Build a DF: 1 revoked + 2001 non-revoked
        revoked_row = {
            "npi": "1111111111",
            "hcpcs_cd": "99213",
            "present_in_2026_revocation_file": 1,
            "revocation_reason_summary": "False claims",
            "present_in_2025_enrollment_file": 0,
            "medicare_participating_ind": "N",
            "peer_case_count": 30,
            "service_volume_peer_z": 4.0,
            "services_per_bene_peer_z": 3.5,
            "submitted_to_allowed_peer_z": 0.5,
            "payment_peer_z": 0.5,
            "peer_avg_tot_srvcs": 150.0,
            "provider_total_benes": 200.0,
        }
        non_revoked_rows = []
        for i in range(2001):
            r = dict(revoked_row)
            r["npi"] = str(2000000000 + i)
            r["present_in_2026_revocation_file"] = 0
            r["revocation_reason_summary"] = None
            non_revoked_rows.append(r)

        df = pl.DataFrame([revoked_row] + non_revoked_rows)

        sc_high = _make_scorecard(risk=75, legitimacy=10, label="high_risk")
        sc_stable = _make_scorecard(risk=10, legitimacy=80, label="stable")

        call_count_tracker = {"n": 0}
        original_side_effects = (
            [sc_high, sc_stable]  # blind + original for the 1 revoked row
            + [sc_stable] * 2001  # non-revoked label pass
            + [sc_stable] * 2001  # non-revoked risk sample
        )

        load_p = patch("src.validation.retrospective.load_cases", return_value=df)
        score_p = patch(
            "src.validation.retrospective.score_case", side_effect=original_side_effects
        )
        with load_p, score_p as mock_score:
            run_validation(Path("/fake/demo.csv"))

        # Non-revoked risk sample is capped at 2000; total calls should be:
        # 2 (revoked blind+orig) + 2001 (non-revoked label) + 2000 (risk sample) = 4003
        assert mock_score.call_count == 4003


# ---------------------------------------------------------------------------
# TestMain
# ---------------------------------------------------------------------------

class TestMain:
    """Tests for the main() entry point."""

    def _fake_results(self) -> dict:
        return {
            "summary": {
                "total_revoked_cases": 100,
                "total_revoked_npis": 50,
                "case_detection_rate": 0.82,
                "npi_detection_rate": 0.9,
                "avg_blind_risk_score_revoked": 55.3,
                "avg_risk_score_non_revoked": 22.1,
                "risk_score_lift": 33.2,
            },
            "case_level": {
                "original_labels": {"high_risk": 80, "review": 15, "stable": 5},
                "blind_labels": {"high_risk": 70, "review": 12, "stable": 18},
            },
            "provider_level": {
                "blind_labels": {"high_risk": 35, "review": 10, "stable": 5},
            },
            "non_revoked_baseline": {"stable": 900, "review": 80, "high_risk": 20},
            "by_revocation_reason": {
                "False claims": {
                    "total": 60,
                    "high_risk": 50,
                    "review": 5,
                    "stable": 5,
                    "detection_rate": 0.917,
                },
            },
        }

    def test_main_calls_run_validation(self):
        """main() calls run_validation() exactly once (with no arguments)."""
        fake_results = self._fake_results()

        with (
            patch(
                "src.validation.retrospective.run_validation",
                return_value=fake_results,
            ) as mock_rv,
            patch("src.validation.retrospective.OUTPUT_DIR") as mock_dir,
            patch("builtins.open", mock_open()),
            patch("json.dump"),
            patch("builtins.print"),
        ):
            mock_dir.mkdir = MagicMock()
            main()

        mock_rv.assert_called_once_with()

    def test_main_creates_output_dir(self):
        """main() calls OUTPUT_DIR.mkdir(parents=True, exist_ok=True)."""
        fake_results = self._fake_results()

        with (
            patch(
                "src.validation.retrospective.run_validation",
                return_value=fake_results,
            ),
            patch("src.validation.retrospective.OUTPUT_DIR") as mock_dir,
            patch("builtins.open", mock_open()),
            patch("json.dump"),
            patch("builtins.print"),
        ):
            mock_dir.__truediv__ = MagicMock(return_value=Path("/fake/out.json"))
            main()

        mock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_main_writes_json(self):
        """main() opens the output path for writing and calls json.dump."""
        fake_results = self._fake_results()
        m = mock_open()

        with (
            patch(
                "src.validation.retrospective.run_validation",
                return_value=fake_results,
            ),
            patch("src.validation.retrospective.OUTPUT_DIR") as mock_dir,
            patch("builtins.open", m),
            patch("json.dump") as mock_dump,
            patch("builtins.print"),
        ):
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = MagicMock(return_value=Path("/fake/out.json"))
            main()

        assert mock_dump.call_count == 1
        # First positional arg to json.dump must be the results dict
        assert mock_dump.call_args[0][0] is fake_results

    def test_main_prints_summary_lines(self):
        """main() prints detection rates and risk scores to stdout."""
        fake_results = self._fake_results()
        printed: list[str] = []

        with (
            patch(
                "src.validation.retrospective.run_validation",
                return_value=fake_results,
            ),
            patch("src.validation.retrospective.OUTPUT_DIR") as mock_dir,
            patch("builtins.open", mock_open()),
            patch("json.dump"),
            patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a[0]) if a else "")),
        ):
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = MagicMock(return_value=Path("/fake/out.json"))
            main()

        combined = "\n".join(printed)
        assert "RETROSPECTIVE VALIDATION RESULTS" in combined
        assert "CASE-LEVEL DETECTION RATE" in combined
        assert "PROVIDER-LEVEL DETECTION RATE" in combined

    def test_main_prints_label_breakdown(self):
        """main() prints blind label breakdown lines and revocation reason lines."""
        fake_results = self._fake_results()
        printed: list[str] = []

        with (
            patch(
                "src.validation.retrospective.run_validation",
                return_value=fake_results,
            ),
            patch("src.validation.retrospective.OUTPUT_DIR") as mock_dir,
            patch("builtins.open", mock_open()),
            patch("json.dump"),
            patch("builtins.print", side_effect=lambda *a, **k: printed.append(str(a[0]) if a else "")),
        ):
            mock_dir.mkdir = MagicMock()
            mock_dir.__truediv__ = MagicMock(return_value=Path("/fake/out.json"))
            main()

        combined = "\n".join(printed)
        assert "high_risk" in combined
        assert "Non-revoked baseline" in combined
        assert "False claims" in combined
