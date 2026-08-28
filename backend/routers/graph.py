"""
/api/graph — Knowledge Graph exploration endpoints.
Returns D3.js-compatible node/edge data for visualization.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from services import neo4j_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/subgraph")
async def get_subgraph(
    disease: str = Query(..., description="Disease name to center the subgraph on"),
    depth: int = Query(2, ge=1, le=3),
):
    """Return disease-centered subgraph for D3 force-directed visualization."""
    try:
        data = await neo4j_service.get_graph_subgraph(disease, depth)
        return {
            "status": "ok",
            "disease": disease,
            "node_count": len(data.get("nodes", [])),
            "edge_count": len(data.get("edges", [])),
            **data,
        }
    except Exception as e:
        logger.warning("Graph subgraph error: %s", e)
        return {
            "status": "neo4j_unavailable",
            "disease": disease,
            "nodes": [],
            "edges": [],
            "note": "Neo4j is not running. Start Neo4j and load PrimeKG data via scripts/init_graph.py",
        }


@router.get("/targets")
async def get_disease_targets(
    disease: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
):
    """Return ranked targets associated with a disease."""
    try:
        targets = await neo4j_service.find_disease_targets(disease, limit)
        return {"disease": disease, "targets": targets, "count": len(targets)}
    except Exception as e:
        return {"disease": disease, "targets": [], "error": str(e)}


@router.get("/compounds")
async def get_target_compounds(
    target_id: str = Query(..., description="Neo4j Target node ID"),
    limit: int = Query(20, ge=1, le=100),
):
    """Return compounds that modulate a given target."""
    try:
        compounds = await neo4j_service.find_target_compounds(target_id, limit)
        return {"target_id": target_id, "compounds": compounds, "count": len(compounds)}
    except Exception as e:
        return {"target_id": target_id, "compounds": [], "error": str(e)}
