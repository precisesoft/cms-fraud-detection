"""Signal and peer comparison endpoints for a specific provider."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from src.api.deps import get_db
from src.api.schemas import Signal
from src.scoring.extract import extract_signals

router = APIRouter(prefix="/providers", tags=["providers"])

# ---------------------------------------------------------------------------
# GET /providers/{npi}/signals
# ---------------------------------------------------------------------------

_CASES_SQL = """
SELECT present_in_2025_enrollment_file,
       present_in_2026_revocation_file,
       medicare_participating_ind,
       provider_total_benes,
       peer_case_count,
       peer_avg_tot_srvcs,
       service_volume_peer_z,
       services_per_bene_peer_z,
       submitted_to_allowed_peer_z,
       payment_peer_z,
       hcpcs_cd,
       hcpcs_desc,
       seed_risk_score,
       seed_legitimacy_score
FROM provider_service_cases
WHERE npi = %s
ORDER BY seed_risk_score DESC NULLS LAST
"""


@router.get("/{npi}/signals", response_model=list[Signal])
async def get_provider_signals(
    npi: str,
    conn: AsyncConnection = Depends(get_db),
) -> list[Signal]:
    """Return all fired signals across a provider's service cases, deduplicated."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_CASES_SQL, [npi])
        rows = await cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No cases found for provider {npi}")

    # Collect unique signals across all cases (dedupe by name + direction)
    seen: set[tuple[str, str]] = set()
    signals: list[Signal] = []

    for row in rows:
        for fs in extract_signals(row):
            key = (fs.signal.name, fs.signal.direction.value)
            if key not in seen:
                seen.add(key)
                signals.append(
                    Signal(
                        name=fs.signal.name,
                        category=fs.signal.category,
                        direction=fs.signal.direction.value,
                        value=fs.value,
                        threshold=fs.signal.threshold,
                        description=fs.reason or fs.signal.description,
                    )
                )

    # Sort: risk signals first, then legitimacy
    signals.sort(key=lambda s: (s.direction != "risk", s.name))
    return signals


# ---------------------------------------------------------------------------
# GET /providers/{npi}/peers
# ---------------------------------------------------------------------------

_PEERS_SQL = """
SELECT hcpcs_cd,
       hcpcs_desc,
       tot_srvcs,
       peer_avg_tot_srvcs,
       service_volume_peer_z,
       services_per_bene,
       services_per_bene_peer_z,
       submitted_to_allowed_ratio,
       submitted_to_allowed_peer_z,
       avg_medicare_payment_amt,
       payment_peer_z,
       peer_scope,
       peer_case_count,
       seed_risk_score,
       seed_case_label
FROM provider_service_cases
WHERE npi = %s
ORDER BY service_volume_peer_z DESC NULLS LAST
"""


class PeerLine(BaseModel):
    """Single service line with provider vs peer comparison data."""

    hcpcs_cd: str
    hcpcs_desc: str | None = None
    tot_srvcs: float | None = None
    peer_avg_tot_srvcs: float | None = None
    service_volume_peer_z: float | None = None
    services_per_bene: float | None = None
    services_per_bene_peer_z: float | None = None
    submitted_to_allowed_ratio: float | None = None
    submitted_to_allowed_peer_z: float | None = None
    avg_medicare_payment_amt: float | None = None
    payment_peer_z: float | None = None
    peer_scope: str | None = None
    peer_case_count: int | None = None
    seed_risk_score: int | None = None
    seed_case_label: str | None = None


class PeerResponse(BaseModel):
    npi: str
    lines: list[PeerLine]
    total_lines: int = Field(description="Number of service lines for this provider")


@router.get("/{npi}/peers", response_model=PeerResponse)
async def get_provider_peers(
    npi: str,
    conn: AsyncConnection = Depends(get_db),
) -> PeerResponse:
    """Return peer comparison data for each service line — feeds provider detail charts."""
    async with conn.cursor(row_factory=dict_row) as cur:
        await cur.execute(_PEERS_SQL, [npi])
        rows = await cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No cases found for provider {npi}")

    lines = [PeerLine(**r) for r in rows]
    return PeerResponse(npi=npi, lines=lines, total_lines=len(lines))
