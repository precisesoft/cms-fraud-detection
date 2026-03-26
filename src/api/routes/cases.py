"""Case actions endpoint — investigation workflow for flagged claims.

POST /api/cases/{case_id}/action records an analyst decision.
GET  /api/cases/{case_id}/actions returns the action history.
GET  /api/cases/pending returns cases awaiting action.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg import AsyncConnection

from src.api.auth import get_current_user
from src.api.deps import get_db
from src.api.routes.audit import write_audit_entry
from src.api.schemas import (
    AuditEventType,
    CaseAction,
    CaseActionRecord,
    CaseActionRequest,
    CaseActionResponse,
    CaseActionsListResponse,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("/{case_id}/action", response_model=CaseActionResponse)
async def record_action(
    case_id: str,
    req: CaseActionRequest,
    request: Request,
    conn: AsyncConnection = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
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
            INSERT INTO case_actions (case_id, npi, action, notes, analyst_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                case_id,
                npi,
                req.action.value,
                req.notes,
                getattr(current_user, "username", "system"),
            ),
        )

    await write_audit_entry(
        conn,
        event_type=AuditEventType.case_action,
        analyst=getattr(current_user, "username", "system"),
        action=req.action.value,
        entity_type="case",
        entity_id=case_id,
        details={"npi": npi, "notes": req.notes},
        ip_address=request.client.host if request.client else None,
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


@router.get("/pending", response_model=dict)
async def list_pending(
    limit: int = 50,
    risk_band: str = "",
    conn: AsyncConnection = Depends(get_db),
) -> dict:
    """Get cases awaiting analyst action (investigation inbox).

    Returns cases across all risk bands by default, or filtered to a
    specific band.  Includes ``total_count`` (untruncated by LIMIT) so
    the UI can show the real scope.

    Falls back to returning cases without join on ``case_actions``
    if that table has not been created yet.
    """
    try:
        return await _pending_with_actions(conn, limit, risk_band)
    except Exception:
        # Rollback the failed transaction before retrying with the fallback
        await conn.rollback()
        logger.warning("case_actions table missing — returning unfiltered cases")
        return await _pending_fallback(conn, limit, risk_band)


async def _pending_with_actions(conn: AsyncConnection, limit: int, risk_band: str) -> dict:
    """Return pending cases excluding those already acted on."""
    band_clause, band_params = _band_clause(risk_band)
    async with conn.cursor() as cur:
        # Total count (without LIMIT)
        await cur.execute(
            f"""
            SELECT COUNT(*) FROM provider_service_cases psc
            LEFT JOIN (
                SELECT DISTINCT ON (case_id) case_id, action
                FROM case_actions
                ORDER BY case_id, created_at DESC
            ) latest ON latest.case_id = psc.case_id
            WHERE latest.case_id IS NULL{band_clause}
            """,
            band_params,
        )
        row = await cur.fetchone()
        total_count = row[0] if row else 0

        # Paginated results
        await cur.execute(
            f"""
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
            WHERE latest.case_id IS NULL{band_clause}
            ORDER BY psc.seed_risk_score DESC
            LIMIT %s
            """,
            (*band_params, limit),
        )
        cols = [desc.name for desc in cur.description] if cur.description else []
        rows = await cur.fetchall()

    return {
        "total_count": total_count,
        "cases": [dict(zip(cols, row)) for row in rows],
    }


async def _pending_fallback(conn: AsyncConnection, limit: int, risk_band: str) -> dict:
    """Return cases without filtering by actions (table missing)."""
    band_clause, band_params = _band_clause_bare(risk_band)
    async with conn.cursor() as cur:
        await cur.execute(
            f"""
            SELECT COUNT(*) FROM provider_service_cases
            WHERE 1=1{band_clause}
            """,
            band_params,
        )
        row = await cur.fetchone()
        total_count = row[0] if row else 0

        await cur.execute(
            f"""
            SELECT case_id, npi,
                   provider_last_org_name,
                   hcpcs_cd, hcpcs_desc,
                   seed_risk_score, seed_case_label,
                   avg_submitted_charge, tot_srvcs
            FROM provider_service_cases
            WHERE 1=1{band_clause}
            ORDER BY seed_risk_score DESC
            LIMIT %s
            """,
            (*band_params, limit),
        )
        cols = [desc.name for desc in cur.description] if cur.description else []
        rows = await cur.fetchall()

    return {
        "total_count": total_count,
        "cases": [dict(zip(cols, row)) for row in rows],
    }


def _band_clause(risk_band: str) -> tuple[str, tuple]:
    """Build optional SQL WHERE fragment with ``psc.`` table alias (for JOINs)."""
    if risk_band in ("high_risk", "review", "stable"):
        return " AND psc.seed_case_label = %s", (risk_band,)
    return "", ()


def _band_clause_bare(risk_band: str) -> tuple[str, tuple]:
    """Build optional SQL WHERE fragment without table alias (single-table queries)."""
    if risk_band in ("high_risk", "review", "stable"):
        return " AND seed_case_label = %s", (risk_band,)
    return "", ()
