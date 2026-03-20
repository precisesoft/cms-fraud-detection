"""Case actions endpoint — investigation workflow for flagged claims.

POST /api/cases/{case_id}/action records an analyst decision.
GET  /api/cases/{case_id}/actions returns the action history.
GET  /api/cases/pending returns cases awaiting action.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from src.api.deps import get_db
from src.api.schemas import (
    CaseAction,
    CaseActionRecord,
    CaseActionRequest,
    CaseActionResponse,
    CaseActionsListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/{case_id}/action", response_model=CaseActionResponse)
async def record_action(
    case_id: str,
    req: CaseActionRequest,
    conn: AsyncConnection = Depends(get_db),
) -> CaseActionResponse:
    """Record an analyst action on a case.

    Works for both real cases (in provider_service_cases) and simulated
    claims where the case_id is constructed as ``npi|hcpcs|pos``.
    """
    async with conn.cursor() as cur:
        # Try to resolve NPI from the cases table first
        await cur.execute(
            "SELECT npi FROM provider_service_cases WHERE case_id = %s",
            (case_id,),
        )
        row = await cur.fetchone()
        npi = row[0] if row else case_id.split("|")[0]

        if not npi:
            raise HTTPException(status_code=400, detail="Cannot resolve NPI from case_id")

        await cur.execute(
            """
            INSERT INTO case_actions (case_id, npi, action, notes)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (case_id, npi, req.action.value, req.notes),
        )
        await conn.commit()

    logger.info("Case %s npi=%s action=%s", case_id, npi, req.action.value)

    return CaseActionResponse(
        case_id=case_id,
        action=req.action,
        message=f"Case {case_id} marked as {req.action.value}",
    )


@router.get("/{case_id}/actions", response_model=CaseActionsListResponse)
async def list_actions(
    case_id: str,
    conn: AsyncConnection = Depends(get_db),
) -> CaseActionsListResponse:
    """Get the action history for a case."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, case_id, npi, action, notes, analyst_id,
                   created_at::text AS created_at
            FROM case_actions
            WHERE case_id = %s
            ORDER BY created_at DESC
            """,
            (case_id,),
        )
        cols = [desc.name for desc in cur.description] if cur.description else []
        rows = await cur.fetchall()

    actions = [CaseActionRecord(**dict(zip(cols, row))) for row in rows]
    current = CaseAction(actions[0].action) if actions else None

    return CaseActionsListResponse(
        case_id=case_id,
        actions=actions,
        current_status=current,
    )


@router.get("/pending", response_model=list[dict])
async def list_pending(
    limit: int = 50,
    conn: AsyncConnection = Depends(get_db),
) -> list[dict]:
    """Get high-risk cases that have no action yet (analyst inbox)."""
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT psc.case_id, psc.npi,
                   psc.provider_last_org_name,
                   psc.hcpcs_cd, psc.hcpcs_desc,
                   psc.seed_risk_score, psc.seed_case_label,
                   psc.avg_submitted_charge, psc.tot_srvcs
            FROM provider_service_cases psc
            LEFT JOIN (
                SELECT DISTINCT ON (case_id) case_id, action
                FROM case_actions
                ORDER BY case_id, created_at DESC
            ) latest ON latest.case_id = psc.case_id
            WHERE latest.case_id IS NULL
              AND psc.seed_risk_score >= 51
            ORDER BY psc.seed_risk_score DESC
            LIMIT %s
            """,
            (limit,),
        )
        cols = [desc.name for desc in cur.description] if cur.description else []
        rows = await cur.fetchall()

    return [dict(zip(cols, row)) for row in rows]
