"""Column mapping definitions for raw CMS CSV source files.

Maps vendor column names (e.g. ``Rndrng_NPI``) to our internal schema names
(e.g. ``npi``) for each of the four supported CMS source types.
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# Source-type identifier
# ---------------------------------------------------------------------------

SOURCE_TYPES = Literal["part_b_service", "part_b_provider", "enrollment", "revocations"]

# ---------------------------------------------------------------------------
# Column mappings  (raw CMS name  →  internal schema name)
# ---------------------------------------------------------------------------

COLUMN_MAPS: dict[str, dict[str, str]] = {
    # Medicare Physician & Other Practitioners — by Provider and Service
    "part_b_service": {
        "Rndrng_NPI": "npi",
        "Rndrng_Prvdr_Last_Org_Name": "provider_last_org_name",
        "Rndrng_Prvdr_First_Name": "provider_first_name",
        "Rndrng_Prvdr_Crdntls": "provider_credentials",
        "Rndrng_Prvdr_Ent_Cd": "provider_entity_code",
        "Rndrng_Prvdr_City": "provider_city",
        "Rndrng_Prvdr_State_Abrvtn": "provider_state",
        "Rndrng_Prvdr_Zip5": "provider_zip5",
        "Rndrng_Prvdr_Type": "provider_type",
        "Rndrng_Prvdr_Mdcr_Prtcptg_Ind": "medicare_participating_ind",
        "HCPCS_Cd": "hcpcs_cd",
        "HCPCS_Desc": "hcpcs_desc",
        "Place_Of_Srvc": "place_of_service",
        "Tot_Benes": "tot_benes",
        "Tot_Srvcs": "tot_srvcs",
        "Tot_Bene_Day_Srvcs": "tot_bene_day_srvcs",
        "Avg_Sbmtd_Chrg": "avg_submitted_charge",
        "Avg_Mdcr_Alowd_Amt": "avg_medicare_allowed_amt",
        "Avg_Mdcr_Pymt_Amt": "avg_medicare_payment_amt",
    },
    # Medicare Physician & Other Practitioners — by Provider (aggregate)
    "part_b_provider": {
        "Rndrng_NPI": "npi",
        "Rndrng_Prvdr_Last_Org_Name": "provider_last_org_name",
        "Rndrng_Prvdr_First_Name": "provider_first_name",
        "Rndrng_Prvdr_City": "provider_city",
        "Rndrng_Prvdr_State_Abrvtn": "provider_state",
        "Rndrng_Prvdr_Zip5": "provider_zip5",
        "Rndrng_Prvdr_Type": "provider_type",
        "Rndrng_Prvdr_Mdcr_Prtcptg_Ind": "medicare_participating",
        "Tot_HCPCS_Cds": "total_hcpcs_codes",
        "Tot_Benes": "total_benes",
        "Tot_Srvcs": "total_services",
        "Tot_Mdcr_Pymt_Amt": "total_payment_amt",
    },
    # PECOS — Medicare Fee-for-Service Public Provider Enrollment
    "enrollment": {
        "NPI": "npi",
        "ENRLMT_ID": "enrollment_id",
        "PROVIDER_TYPE_CODE": "provider_type_cd",
        "PROVIDER_TYPE_DESC": "provider_type_desc",
        "STATE_CD": "state_cd",
    },
    # CMS Medicare Revocation / Opt-Out file
    "revocations": {
        "NPI": "npi",
        "REVOCATION_RSN": "revocation_reason",
    },
}

# ---------------------------------------------------------------------------
# Required columns — must be present or the file is rejected
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: dict[str, list[str]] = {
    "part_b_service": [
        "Rndrng_NPI",
        "HCPCS_Cd",
        "Tot_Benes",
        "Tot_Srvcs",
        "Avg_Sbmtd_Chrg",
        "Avg_Mdcr_Alowd_Amt",
        "Avg_Mdcr_Pymt_Amt",
    ],
    "part_b_provider": [
        "Rndrng_NPI",
        "Tot_HCPCS_Cds",
        "Tot_Benes",
        "Tot_Srvcs",
        "Tot_Mdcr_Pymt_Amt",
    ],
    "enrollment": [
        "NPI",
        "ENRLMT_ID",
        "STATE_CD",
    ],
    "revocations": [
        "NPI",
        "REVOCATION_RSN",
    ],
}

# ---------------------------------------------------------------------------
# Target Postgres raw table names
# ---------------------------------------------------------------------------

RAW_TABLE_NAMES: dict[str, str] = {
    "part_b_service": "raw_part_b_service",
    "part_b_provider": "raw_part_b_provider",
    "enrollment": "raw_enrollment",
    "revocations": "raw_revocations",
}
