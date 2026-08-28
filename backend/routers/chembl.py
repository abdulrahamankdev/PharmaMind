"""
/api/chembl — ChEMBL bioactivity passthrough endpoints.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Query
from services import chembl_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/activities")
async def get_activities(
    target_id: str = Query(..., description="ChEMBL target ID (e.g., CHEMBL2366517)"),
    activity_type: str = Query("IC50", description="Activity type: IC50, Ki, EC50, etc."),
    limit: int = Query(25, ge=1, le=100),
):
    """Retrieve bioactivity records from ChEMBL for a given target."""
    try:
        activities = await chembl_service.search_activities_by_target(
            target_id, activity_type, limit
        )
        return {"target_id": target_id, "activity_type": activity_type, "activities": activities, "count": len(activities)}
    except Exception as e:
        logger.error("ChEMBL activities error: %s", e)
        return {"target_id": target_id, "activities": [], "error": str(e)}


@router.get("/target-search")
async def search_target(
    gene: str = Query(..., description="Gene symbol (e.g., BACE1, EGFR)"),
    limit: int = Query(5),
):
    """Search ChEMBL targets by gene symbol."""
    try:
        results = await chembl_service.search_target_by_gene(gene, limit)
        return {"gene": gene, "targets": results}
    except Exception as e:
        return {"gene": gene, "targets": [], "error": str(e)}


@router.get("/compound/{chembl_id}")
async def get_compound(chembl_id: str):
    """Get detailed compound information from ChEMBL."""
    try:
        compound = await chembl_service.get_compound_details(chembl_id)
        return {"compound": compound}
    except Exception as e:
        return {"compound": None, "error": str(e)}
