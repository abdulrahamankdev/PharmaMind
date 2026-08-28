"""
/api/query — Main research orchestration endpoint.
Coordinates: KG lookup → ChEMBL bioactivity → PubMed literature → AI hypothesis → scoring.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from services import neo4j_service, chembl_service, pubmed_service, scoring_service
from agents import hypothesis_agent, refuter_agent

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    disease: str = Field(..., description="Disease name (e.g., 'Alzheimer disease')")
    target: str = Field(..., description="Target gene/protein (e.g., 'BACE1')")
    compound: str | None = Field(None, description="Optional compound name or ChEMBL ID")
    run_adversarial: bool = Field(True, description="Run adversarial refuter agent")
    max_compounds: int = Field(10, ge=1, le=50)
    max_pubmed: int = Field(8, ge=1, le=20)


class QueryResponse(BaseModel):
    query_id: str
    disease: str
    target: str
    compound: str | None
    processing_time_s: float
    knowledge_graph: dict[str, Any]
    ranked_candidates: list[dict[str, Any]]
    hypothesis: dict[str, Any]
    refutation: dict[str, Any] | None
    literature: list[dict[str, Any]]
    disclaimer: str
    system_metadata: dict[str, Any]


@router.post("/", response_model=QueryResponse)
async def run_research_query(req: QueryRequest):
    """
    Full PharmaMind pipeline:
    1. KG subgraph retrieval
    2. ChEMBL bioactivity data
    3. PubMed literature
    4. Degree-agnostic candidate scoring
    5. Hypothesis generation (Ollama)
    6. Adversarial refutation (Ollama)
    """
    t0 = time.perf_counter()
    query_id = f"QID-{int(time.time())}"
    logger.info("Starting query %s: disease=%s target=%s", query_id, req.disease, req.target)

    # ── Step 1: Knowledge Graph ────────────────────────────────────────────
    kg_data = {"nodes": [], "edges": []}
    try:
        kg_data = await neo4j_service.get_graph_subgraph(req.disease)
        targets_from_kg = await neo4j_service.find_disease_targets(req.disease, limit=20)
        compounds_from_kg = []
        if targets_from_kg:
            first_target_id = targets_from_kg[0].get("target_id", "")
            compounds_from_kg = await neo4j_service.find_target_compounds(
                first_target_id, limit=req.max_compounds
            )
    except Exception as e:
        logger.warning("Neo4j unavailable or error: %s — proceeding without KG data", e)
        targets_from_kg   = []
        compounds_from_kg = []

    # ── Step 2: ChEMBL Bioactivity ─────────────────────────────────────────
    chembl_activities: list[dict] = []
    try:
        # Search ChEMBL by gene symbol
        chembl_targets = await chembl_service.search_target_by_gene(req.target, limit=3)
        for ct in chembl_targets[:2]:
            acts = await chembl_service.search_activities_by_target(
                ct["target_chembl_id"], limit=req.max_compounds
            )
            chembl_activities.extend(acts)
    except Exception as e:
        logger.warning("ChEMBL API error: %s", e)

    # ── Step 3: PubMed Literature ──────────────────────────────────────────
    pubmed_articles: list[dict] = []
    try:
        search_query = f"{req.disease}[MeSH] AND {req.target}[Gene] AND drug therapy"
        pubmed_articles = await pubmed_service.search_pubmed(
            search_query, max_results=req.max_pubmed
        )
    except Exception as e:
        logger.warning("PubMed API error: %s", e)

    # ── Step 4: Degree-Agnostic Scoring ────────────────────────────────────
    # Build candidate list from ChEMBL + KG
    candidates: list[dict] = []
    seen_ids: set[str] = set()

    for act in chembl_activities:
        cid = act.get("molecule_chembl_id", "")
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            # Get degree from KG nodes if available
            degree = sum(
                1 for n in kg_data.get("nodes", [])
                if n.get("id") == cid
            ) or 1

            compound_dict = {
                "compound_id":      cid,
                "compound_name":    act.get("compound_name") or cid,
                "smiles":           act.get("smiles"),
                "molecular_weight": None,
                "alogp":            None,
                "hbd":              None,
                "hba":              None,
            }

            relevant_acts = [a for a in chembl_activities if a.get("molecule_chembl_id") == cid]
            score_report = scoring_service.compute_candidate_score(
                compound_dict, relevant_acts, degree_in_graph=degree
            )

            candidates.append({
                **compound_dict,
                **score_report,
                "source": "ChEMBL",
            })

    ranked = scoring_service.rank_candidates(candidates)[:req.max_compounds]

    # ── Step 5: Hypothesis Generation ─────────────────────────────────────
    hypothesis: dict = {}
    try:
        hypothesis = await hypothesis_agent.generate_hypothesis(
            disease=req.disease,
            target=req.target,
            compound=req.compound or (ranked[0]["compound_name"] if ranked else None),
            kg_context=kg_data.get("nodes", []),
            chembl_context=chembl_activities[:10],
            pubmed_context=pubmed_articles[:6],
        )
    except Exception as e:
        logger.error("Hypothesis agent failed: %s", e)
        hypothesis = {
            "error": str(e),
            "note": "Ensure Ollama is running: `ollama serve && ollama pull llama3`",
            "disclaimer": "Research tool only. Not medical advice.",
        }

    # ── Step 6: Adversarial Refutation ────────────────────────────────────
    refutation: dict | None = None
    if req.run_adversarial and hypothesis and "error" not in hypothesis:
        try:
            refutation = await refuter_agent.refute_hypothesis(
                hypothesis=hypothesis,
                chembl_activities=chembl_activities[:12],
                off_target_activities=[a for a in chembl_activities if a.get("target_chembl_id") != (chembl_targets[0]["target_chembl_id"] if chembl_targets else "")][:8],
            )
        except Exception as e:
            logger.error("Refuter agent failed: %s", e)
            refutation = {"error": str(e)}

    elapsed = round(time.perf_counter() - t0, 2)

    return QueryResponse(
        query_id=query_id,
        disease=req.disease,
        target=req.target,
        compound=req.compound,
        processing_time_s=elapsed,
        knowledge_graph=kg_data,
        ranked_candidates=ranked,
        hypothesis=hypothesis,
        refutation=refutation,
        literature=pubmed_articles,
        disclaimer=(
            "⚠️ PharmaMind is an exploratory research-support tool. "
            "All outputs are hypotheses for scientific investigation only. "
            "This system does NOT make medical decisions and must NOT be used for clinical purposes."
        ),
        system_metadata={
            "query_id":        query_id,
            "kg_nodes":        len(kg_data.get("nodes", [])),
            "kg_edges":        len(kg_data.get("edges", [])),
            "chembl_records":  len(chembl_activities),
            "pubmed_articles": len(pubmed_articles),
            "candidates_ranked": len(ranked),
        },
    )


@router.get("/search")
async def search_entities(q: str = Query(..., min_length=2)):
    """Quick entity search across Disease, Target, Compound nodes in KG."""
    try:
        results = await neo4j_service.search_nodes(q, limit=15)
        return {"query": q, "results": results}
    except Exception as e:
        logger.warning("KG search failed: %s", e)
        return {"query": q, "results": [], "note": "KG unavailable — ensure Neo4j is running."}
