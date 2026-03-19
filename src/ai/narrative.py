"""Risk narrative generator — AI-powered investigation briefs.

Takes structured scoring data (signals, risk score, provider context) and
generates a concise human-readable narrative using Claude via Bedrock.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ai.bedrock import NARRATIVE_MODEL, invoke
from src.ai.prompts import NARRATIVE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


async def generate_narrative(
    *,
    npi: str,
    risk_score: int,
    risk_band: str,
    signals: list[dict[str, Any]],
    provider_name: str | None = None,
    provider_type: str | None = None,
    state: str | None = None,
    recommendation: str | None = None,
    peer_comparisons: list[dict[str, Any]] | None = None,
) -> str | None:
    """Generate a risk narrative from structured scoring data.

    Returns the narrative string, or None if generation fails (non-fatal).
    """
    # Build a structured summary for Claude
    risk_signals = [s for s in signals if s.get("direction") == "risk"]
    legit_signals = [s for s in signals if s.get("direction") == "legitimacy"]

    parts = [
        f"Provider: {provider_name or 'Unknown'} (NPI: {npi})",
        f"Type: {provider_type or 'Unknown'}",
        f"State: {state or 'Unknown'}",
        f"Risk Score: {risk_score}/100 (Band: {risk_band})",
    ]

    if recommendation:
        parts.append(f"Recommendation: {recommendation.upper()}")

    if risk_signals:
        signal_lines = []
        for s in risk_signals:
            desc = s.get("description", s.get("name", "unknown"))
            val = s.get("value")
            if val is not None:
                signal_lines.append(f"  - {desc} (value: {val})")
            else:
                signal_lines.append(f"  - {desc}")
        parts.append("Risk Signals:\n" + "\n".join(signal_lines))

    if legit_signals:
        signal_lines = []
        for s in legit_signals:
            desc = s.get("description", s.get("name", "unknown"))
            signal_lines.append(f"  - {desc}")
        parts.append("Legitimacy Signals:\n" + "\n".join(signal_lines))

    if peer_comparisons:
        peer_lines = []
        for p in peer_comparisons:
            metric = p.get("metric", "unknown")
            prov_val = p.get("provider_value", 0)
            peer_mean = p.get("peer_mean", 0)
            z = p.get("z_score", 0)
            peer_lines.append(
                f"  - {metric}: provider={prov_val}, peer_mean={peer_mean}, z={z:.1f}"
            )
        parts.append("Peer Comparisons:\n" + "\n".join(peer_lines))

    user_message = "\n".join(parts)

    try:
        response = await invoke(
            messages=[{"role": "user", "content": user_message}],
            system=NARRATIVE_SYSTEM_PROMPT,
            model=NARRATIVE_MODEL,
            max_tokens=300,
            temperature=0.3,
        )
        narrative: str = response["text"].strip()
        logger.info("narrative generated for NPI=%s (%d chars)", npi, len(narrative))
        return narrative
    except Exception:
        logger.exception("narrative generation failed for NPI=%s", npi)
        return None
