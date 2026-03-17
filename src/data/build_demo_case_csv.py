from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw" / "public_sources" / "cms"
OUTPUT_DIR = ROOT / "data" / "processed" / "demo"
OUTPUT_CSV = OUTPUT_DIR / "provider_service_cases_demo.csv"
TEMP_DIR = ROOT / "data" / "processed" / "duckdb_tmp"


def build_demo_case_csv() -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    part_b_provider = (RAW_DIR / "part_b_provider_2023.csv").as_posix()
    part_b_provider_service = (RAW_DIR / "part_b_provider_service_2023.csv").as_posix()
    public_provider_enrollment = (RAW_DIR / "public_provider_enrollment_q4_2025.csv").as_posix()
    revoked_providers = (RAW_DIR / "revoked_providers_q1_2026.csv").as_posix()
    output_csv = OUTPUT_CSV.as_posix()
    temp_dir = TEMP_DIR.as_posix()

    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    con.execute(f"PRAGMA temp_directory='{temp_dir}'")

    export_query = f"""
    WITH
    service AS (
      SELECT
        CAST(Rndrng_NPI AS VARCHAR) AS npi,
        Rndrng_Prvdr_Last_Org_Name AS provider_last_org_name,
        Rndrng_Prvdr_First_Name AS provider_first_name,
        Rndrng_Prvdr_Crdntls AS provider_credentials,
        Rndrng_Prvdr_Ent_Cd AS provider_entity_code,
        Rndrng_Prvdr_City AS provider_city,
        Rndrng_Prvdr_State_Abrvtn AS provider_state,
        Rndrng_Prvdr_Zip5 AS provider_zip5,
        Rndrng_Prvdr_Type AS provider_type,
        Rndrng_Prvdr_Mdcr_Prtcptg_Ind AS medicare_participating_ind,
        HCPCS_Cd AS hcpcs_cd,
        HCPCS_Desc AS hcpcs_desc,
        Place_Of_Srvc AS place_of_service,
        CAST(Tot_Benes AS DOUBLE) AS tot_benes,
        CAST(Tot_Srvcs AS DOUBLE) AS tot_srvcs,
        CAST(Tot_Bene_Day_Srvcs AS DOUBLE) AS tot_bene_day_srvcs,
        CAST(Avg_Sbmtd_Chrg AS DOUBLE) AS avg_submitted_charge,
        CAST(Avg_Mdcr_Alowd_Amt AS DOUBLE) AS avg_medicare_allowed_amt,
        CAST(Avg_Mdcr_Pymt_Amt AS DOUBLE) AS avg_medicare_payment_amt
      FROM read_csv_auto(
        '{part_b_provider_service}',
        header=true,
        sample_size=50000
      )
      WHERE Tot_Benes IS NOT NULL
        AND Tot_Srvcs IS NOT NULL
        AND Avg_Mdcr_Alowd_Amt IS NOT NULL
        AND CAST(Tot_Benes AS DOUBLE) >= 11
        AND CAST(Tot_Srvcs AS DOUBLE) >= 11
        AND CAST(Avg_Mdcr_Alowd_Amt AS DOUBLE) > 0
    ),
    provider AS (
      SELECT
        CAST(Rndrng_NPI AS VARCHAR) AS npi,
        CAST(Tot_HCPCS_Cds AS DOUBLE) AS provider_total_hcpcs_codes,
        CAST(Tot_Benes AS DOUBLE) AS provider_total_benes,
        CAST(Tot_Srvcs AS DOUBLE) AS provider_total_services,
        CAST(Tot_Mdcr_Pymt_Amt AS DOUBLE) AS provider_total_payment_amt
      FROM read_csv_auto(
        '{part_b_provider}',
        header=true,
        sample_size=50000
      )
      WHERE Rndrng_NPI IS NOT NULL
    ),
    enrollment AS (
      SELECT
        CAST(NPI AS VARCHAR) AS npi,
        1 AS present_in_2025_enrollment_file,
        COUNT(DISTINCT ENRLMT_ID) AS enrollment_record_count,
        MIN(PROVIDER_TYPE_DESC) AS enrollment_provider_type_desc,
        MIN(STATE_CD) AS enrollment_state_cd
      FROM read_csv_auto(
        '{public_provider_enrollment}',
        header=true,
        sample_size=20000,
        all_varchar=true,
        ignore_errors=true,
        strict_mode=false
      )
      WHERE NPI IS NOT NULL
        AND TRIM(NPI) <> ''
      GROUP BY 1
    ),
    revoked AS (
      SELECT
        CAST(NPI AS VARCHAR) AS npi,
        1 AS present_in_2026_revocation_file,
        STRING_AGG(DISTINCT REVOCATION_RSN, ' | ') AS revocation_reason_summary
      FROM read_csv_auto(
        '{revoked_providers}',
        header=true,
        sample_size=10000,
        all_varchar=true
      )
      WHERE NPI IS NOT NULL
        AND TRIM(NPI) <> ''
      GROUP BY 1
    ),
    base AS (
      SELECT
        CONCAT_WS('|', s.npi, s.hcpcs_cd, s.place_of_service) AS case_id,
        s.*,
        p.provider_total_hcpcs_codes,
        p.provider_total_benes,
        p.provider_total_services,
        p.provider_total_payment_amt,
        COALESCE(e.present_in_2025_enrollment_file, 0) AS present_in_2025_enrollment_file,
        COALESCE(e.enrollment_record_count, 0) AS enrollment_record_count,
        e.enrollment_provider_type_desc,
        e.enrollment_state_cd,
        COALESCE(r.present_in_2026_revocation_file, 0) AS present_in_2026_revocation_file,
        r.revocation_reason_summary,
        ROUND(s.tot_srvcs / NULLIF(s.tot_benes, 0), 4) AS services_per_bene,
        ROUND(s.avg_submitted_charge / NULLIF(s.avg_medicare_allowed_amt, 0), 4) AS submitted_to_allowed_ratio,
        ROUND(s.avg_medicare_payment_amt / NULLIF(s.avg_medicare_allowed_amt, 0), 4) AS payment_to_allowed_ratio,
        ROUND(s.tot_srvcs * s.avg_medicare_payment_amt, 2) AS estimated_case_payment_amt
      FROM service s
      LEFT JOIN provider p USING (npi)
      LEFT JOIN enrollment e USING (npi)
      LEFT JOIN revoked r USING (npi)
    ),
    peer_state AS (
      SELECT
        provider_type,
        provider_state,
        hcpcs_cd,
        place_of_service,
        COUNT(*) AS peer_case_count_state,
        AVG(tot_srvcs) AS peer_avg_tot_srvcs_state,
        STDDEV_POP(tot_srvcs) AS peer_std_tot_srvcs_state,
        AVG(services_per_bene) AS peer_avg_services_per_bene_state,
        STDDEV_POP(services_per_bene) AS peer_std_services_per_bene_state,
        AVG(submitted_to_allowed_ratio) AS peer_avg_charge_ratio_state,
        STDDEV_POP(submitted_to_allowed_ratio) AS peer_std_charge_ratio_state,
        AVG(avg_medicare_payment_amt) AS peer_avg_payment_state,
        STDDEV_POP(avg_medicare_payment_amt) AS peer_std_payment_state
      FROM base
      GROUP BY 1, 2, 3, 4
    ),
    peer_national AS (
      SELECT
        provider_type,
        hcpcs_cd,
        place_of_service,
        COUNT(*) AS peer_case_count_national,
        AVG(tot_srvcs) AS peer_avg_tot_srvcs_national,
        STDDEV_POP(tot_srvcs) AS peer_std_tot_srvcs_national,
        AVG(services_per_bene) AS peer_avg_services_per_bene_national,
        STDDEV_POP(services_per_bene) AS peer_std_services_per_bene_national,
        AVG(submitted_to_allowed_ratio) AS peer_avg_charge_ratio_national,
        STDDEV_POP(submitted_to_allowed_ratio) AS peer_std_charge_ratio_national,
        AVG(avg_medicare_payment_amt) AS peer_avg_payment_national,
        STDDEV_POP(avg_medicare_payment_amt) AS peer_std_payment_national
      FROM base
      GROUP BY 1, 2, 3
    ),
    features AS (
      SELECT
        b.*,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN 'state_specific'
          ELSE 'national_fallback'
        END AS peer_scope,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_case_count_state
          ELSE pn.peer_case_count_national
        END AS peer_case_count,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_avg_tot_srvcs_state
          ELSE pn.peer_avg_tot_srvcs_national
        END AS peer_avg_tot_srvcs,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_std_tot_srvcs_state
          ELSE pn.peer_std_tot_srvcs_national
        END AS peer_std_tot_srvcs,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_avg_services_per_bene_state
          ELSE pn.peer_avg_services_per_bene_national
        END AS peer_avg_services_per_bene,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_std_services_per_bene_state
          ELSE pn.peer_std_services_per_bene_national
        END AS peer_std_services_per_bene,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_avg_charge_ratio_state
          ELSE pn.peer_avg_charge_ratio_national
        END AS peer_avg_charge_ratio,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_std_charge_ratio_state
          ELSE pn.peer_std_charge_ratio_national
        END AS peer_std_charge_ratio,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_avg_payment_state
          ELSE pn.peer_avg_payment_national
        END AS peer_avg_payment,
        CASE
          WHEN COALESCE(ps.peer_case_count_state, 0) >= 25 THEN ps.peer_std_payment_state
          ELSE pn.peer_std_payment_national
        END AS peer_std_payment
      FROM base b
      LEFT JOIN peer_state ps
        ON b.provider_type = ps.provider_type
       AND b.provider_state = ps.provider_state
       AND b.hcpcs_cd = ps.hcpcs_cd
       AND b.place_of_service = ps.place_of_service
      LEFT JOIN peer_national pn
        ON b.provider_type = pn.provider_type
       AND b.hcpcs_cd = pn.hcpcs_cd
       AND b.place_of_service = pn.place_of_service
    ),
    z_scored AS (
      SELECT
        *,
        ROUND(
          CASE
            WHEN COALESCE(peer_std_tot_srvcs, 0) = 0 THEN 0
            ELSE (tot_srvcs - peer_avg_tot_srvcs) / peer_std_tot_srvcs
          END,
          4
        ) AS service_volume_peer_z,
        ROUND(
          CASE
            WHEN COALESCE(peer_std_services_per_bene, 0) = 0 THEN 0
            ELSE (services_per_bene - peer_avg_services_per_bene) / peer_std_services_per_bene
          END,
          4
        ) AS services_per_bene_peer_z,
        ROUND(
          CASE
            WHEN COALESCE(peer_std_charge_ratio, 0) = 0 THEN 0
            ELSE (submitted_to_allowed_ratio - peer_avg_charge_ratio) / peer_std_charge_ratio
          END,
          4
        ) AS submitted_to_allowed_peer_z,
        ROUND(
          CASE
            WHEN COALESCE(peer_std_payment, 0) = 0 THEN 0
            ELSE (avg_medicare_payment_amt - peer_avg_payment) / peer_std_payment
          END,
          4
        ) AS payment_peer_z
      FROM features
    ),
    scored AS (
      SELECT
        *,
        LEAST(
          100,
          CASE WHEN present_in_2026_revocation_file = 1 THEN 25 ELSE 0 END
          + CASE WHEN present_in_2025_enrollment_file = 0 THEN 8 ELSE 0 END
          + CASE
              WHEN peer_case_count >= 25 AND service_volume_peer_z >= 5 THEN 20
              WHEN peer_case_count >= 25 AND service_volume_peer_z >= 3 THEN 14
              WHEN peer_case_count >= 25 AND service_volume_peer_z >= 2 THEN 8
              ELSE 0
            END
          + CASE
              WHEN peer_case_count >= 25 AND services_per_bene_peer_z >= 5 THEN 18
              WHEN peer_case_count >= 25 AND services_per_bene_peer_z >= 3 THEN 12
              WHEN peer_case_count >= 25 AND services_per_bene_peer_z >= 2 THEN 7
              ELSE 0
            END
          + CASE
              WHEN peer_case_count >= 25 AND submitted_to_allowed_peer_z >= 5 THEN 18
              WHEN peer_case_count >= 25 AND submitted_to_allowed_peer_z >= 3 THEN 12
              WHEN peer_case_count >= 25 AND submitted_to_allowed_peer_z >= 2 THEN 7
              ELSE 0
            END
          + CASE
              WHEN peer_case_count >= 25 AND payment_peer_z >= 5 THEN 12
              WHEN peer_case_count >= 25 AND payment_peer_z >= 3 THEN 8
              WHEN peer_case_count >= 25 AND payment_peer_z >= 2 THEN 5
              ELSE 0
            END
        ) AS seed_risk_score,
        LEAST(
          100,
          CASE WHEN present_in_2025_enrollment_file = 1 THEN 20 ELSE 0 END
          + CASE WHEN present_in_2026_revocation_file = 0 THEN 15 ELSE 0 END
          + CASE WHEN medicare_participating_ind = 'Y' THEN 10 ELSE 0 END
          + CASE WHEN peer_case_count >= 25 AND ABS(service_volume_peer_z) < 1 THEN 12 ELSE 0 END
          + CASE WHEN peer_case_count >= 25 AND ABS(services_per_bene_peer_z) < 1 THEN 12 ELSE 0 END
          + CASE WHEN peer_case_count >= 25 AND ABS(submitted_to_allowed_peer_z) < 1 THEN 12 ELSE 0 END
          + CASE WHEN COALESCE(provider_total_benes, 0) >= 100 THEN 8 ELSE 0 END
        ) AS seed_legitimacy_score
      FROM z_scored
    ),
    labeled AS (
      SELECT
        *,
        CASE
          WHEN seed_risk_score >= 50 AND seed_risk_score >= seed_legitimacy_score + 5 THEN 'high_risk'
          WHEN seed_legitimacy_score >= 70 AND seed_risk_score < 30 THEN 'stable'
          ELSE 'review'
        END AS seed_case_label,
        CONCAT_WS(
          '|',
          CASE WHEN present_in_2026_revocation_file = 1 THEN 'revoked_provider' END,
          CASE WHEN present_in_2025_enrollment_file = 0 THEN 'not_in_current_enrollment_file' END,
          CASE WHEN peer_case_count >= 25 AND service_volume_peer_z >= 3 THEN 'service_volume_outlier' END,
          CASE WHEN peer_case_count >= 25 AND services_per_bene_peer_z >= 3 THEN 'service_intensity_outlier' END,
          CASE WHEN peer_case_count >= 25 AND submitted_to_allowed_peer_z >= 3 THEN 'charge_ratio_outlier' END,
          CASE WHEN peer_case_count >= 25 AND payment_peer_z >= 3 THEN 'payment_outlier' END
        ) AS seed_risk_reasons,
        CONCAT_WS(
          '|',
          CASE WHEN present_in_2025_enrollment_file = 1 THEN 'present_in_current_enrollment_file' END,
          CASE WHEN present_in_2026_revocation_file = 0 THEN 'no_revocation_match' END,
          CASE WHEN medicare_participating_ind = 'Y' THEN 'medicare_participating' END,
          CASE WHEN peer_case_count >= 25 AND ABS(service_volume_peer_z) < 1 THEN 'peer_aligned_volume' END,
          CASE WHEN peer_case_count >= 25 AND ABS(services_per_bene_peer_z) < 1 THEN 'peer_aligned_intensity' END,
          CASE WHEN peer_case_count >= 25 AND ABS(submitted_to_allowed_peer_z) < 1 THEN 'peer_aligned_pricing' END
        ) AS seed_legitimacy_reasons
      FROM scored
    ),
    high_risk_ranked AS (
      SELECT
        *,
        ROW_NUMBER() OVER (
          ORDER BY seed_risk_score DESC, estimated_case_payment_amt DESC, npi, hcpcs_cd
        ) AS sample_rank
      FROM labeled
      WHERE seed_case_label = 'high_risk'
    ),
    review_ranked AS (
      SELECT
        *,
        ROW_NUMBER() OVER (
          ORDER BY seed_risk_score DESC, estimated_case_payment_amt DESC, npi, hcpcs_cd
        ) AS sample_rank
      FROM labeled
      WHERE seed_case_label = 'review'
    ),
    stable_ranked AS (
      SELECT
        *,
        ROW_NUMBER() OVER (
          ORDER BY seed_legitimacy_score DESC, estimated_case_payment_amt DESC, npi, hcpcs_cd
        ) AS sample_rank
      FROM labeled
      WHERE seed_case_label = 'stable'
    ),
    final_export AS (
      SELECT * FROM high_risk_ranked WHERE sample_rank <= 7000
      UNION ALL
      SELECT * FROM review_ranked WHERE sample_rank <= 7000
      UNION ALL
      SELECT * FROM stable_ranked WHERE sample_rank <= 6000
    )
    SELECT
      case_id,
      npi,
      provider_last_org_name,
      provider_first_name,
      provider_credentials,
      provider_entity_code,
      provider_city,
      provider_state,
      provider_zip5,
      provider_type,
      medicare_participating_ind,
      hcpcs_cd,
      hcpcs_desc,
      place_of_service,
      tot_benes,
      tot_srvcs,
      tot_bene_day_srvcs,
      avg_submitted_charge,
      avg_medicare_allowed_amt,
      avg_medicare_payment_amt,
      estimated_case_payment_amt,
      services_per_bene,
      submitted_to_allowed_ratio,
      payment_to_allowed_ratio,
      provider_total_hcpcs_codes,
      provider_total_benes,
      provider_total_services,
      provider_total_payment_amt,
      present_in_2025_enrollment_file,
      enrollment_record_count,
      enrollment_provider_type_desc,
      enrollment_state_cd,
      present_in_2026_revocation_file,
      revocation_reason_summary,
      peer_scope,
      peer_case_count,
      peer_avg_tot_srvcs,
      service_volume_peer_z,
      services_per_bene_peer_z,
      submitted_to_allowed_peer_z,
      payment_peer_z,
      seed_risk_score,
      seed_legitimacy_score,
      seed_case_label,
      seed_risk_reasons,
      seed_legitimacy_reasons
    FROM final_export
    ORDER BY
      CASE seed_case_label
        WHEN 'high_risk' THEN 1
        WHEN 'review' THEN 2
        ELSE 3
      END,
      seed_risk_score DESC,
      estimated_case_payment_amt DESC
    """

    con.execute(f"CREATE OR REPLACE TEMP TABLE demo_case_export AS {export_query}")
    con.execute(f"COPY demo_case_export TO '{output_csv}' WITH (FORMAT CSV, HEADER, DELIMITER ',')")

    summary = con.execute(
        """
        SELECT
          seed_case_label,
          COUNT(*) AS row_count,
          ROUND(AVG(seed_risk_score), 2) AS avg_risk_score,
          ROUND(AVG(seed_legitimacy_score), 2) AS avg_legitimacy_score
        FROM demo_case_export
        GROUP BY 1
        ORDER BY 1
        """
    ).fetchall()
    row = con.execute("SELECT COUNT(*) FROM demo_case_export").fetchone()
    total_rows = row[0] if row else 0

    print(f"Created {output_csv}")
    print(f"Total rows: {total_rows}")
    for label, row_count, avg_risk, avg_legitimacy in summary:
        print(
            f"{label}: rows={row_count}, avg_risk_score={avg_risk}, "
            f"avg_legitimacy_score={avg_legitimacy}"
        )

    return OUTPUT_CSV


if __name__ == "__main__":
    build_demo_case_csv()
