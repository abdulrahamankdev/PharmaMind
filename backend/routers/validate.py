"""
/api/validate — Standalone adversarial validation endpoint.
Accepts a pre-formed hypothesis JSON and runs both agents.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents import hypothesis_agent, refuter_agent
from services import chembl_service

logger = logging.getLogger(__name__)
router = APIRouter()


class ValidateRequest(BaseModel):
    disease: str
    target: str
    compound: str | None = None
    hypothesis: dict[str, Any] | None = Field(
        None, description="Pre-formed hypothesis to refute directly (skips generation)"
    )
    target_chembl_id: str | None = Field(
        None, description="ChEMBL target ID to fetch activities for refutation"
    )


@router.post("/")
async def validate_hypothesis(req: ValidateRequest):
    """
    Run the full adversarial validation pipeline:
    1. Generate hypothesis (if not provided)
    2. Fetch ChEMBL activities for refutation
    3. Run adversarial refuter agent
    Returns both hypothesis + refutation in a reasoning trail.
    """
    # ── Step 1: Use provided hypothesis or generate one ────────────────────
    hypothesis = req.hypothesis
    if not hypothesis:
        try:
            hypothesis = await hypothesis_agent.generate_hypothesis(
                disease=req.disease,
                target=req.target,
                compound=req.compound,
            )
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Hypothesis agent failed: {e}")

    # ── Step 2: Fetch ChEMBL Activities ────────────────────────────────────
    chembl_acts: list[dict] = []
    if req.target_chembl_id:
        try:
            chembl_acts = await chembl_service.search_activities_by_target(
                req.target_chembl_id, limit=20
            )
        except Exception as e:
            logger.warning("ChEMBL fetch failed for validation: %s", e)

    # ── Step 3: Adversarial Refutation ─────────────────────────────────────
    try:
        refutation = await refuter_agent.refute_hypothesis(
            hypothesis=hypothesis,
            chembl_activities=chembl_acts,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Refuter agent failed: {e}")

    # ── Build reasoning trail ──────────────────────────────────────────────
    verdict = refutation.get("overall_verdict", "UNKNOWN")
    recommendation = refutation.get("final_recommendation", "UNKNOWN")

    return {
        "pipeline": "adversarial_validation",
        "disease":  req.disease,
        "target":   req.target,
        "compound": req.compound,
        "verdict":  verdict,
        "final_recommendation": recommendation,
        "reasoning_trail": {
            "step_1_hypothesis":  hypothesis,
            "step_2_refutation":  refutation,
            "step_3_summary": {
                "verdict":                verdict,
                "false_positive_risk":    refutation.get("false_positive_risk"),
                "refutation_point_count": len(refutation.get("refutation_points", [])),
                "ooc_experiments":        [
                    e for e in refutation.get("recommended_experiments", [])
                    if e.get("ooc_applicable")
                ],
                "key_citations": (
                    hypothesis.get("citations", [])[:3]
                    + refutation.get("citations", [])[:3]
                ),
            },
        },
        "disclaimer": (
            "⚠️ This adversarial validation is for exploratory research only. "
            "It does not constitute medical advice or a clinical decision."
        ),
    }
