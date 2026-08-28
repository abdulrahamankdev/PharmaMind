"""
Scoring Service — degree-agnostic compound ranking.

Key design decisions:
  - Penalizes "hub" compounds (high degree centrality) to prevent popularity bias
  - Normalizes pChEMBL value to [0,1] scale
  - Flags organ-on-a-chip (OoC) eligible candidates based on MW + selectivity
  - Returns a composite score with sub-score breakdown for transparency
"""
from __future__ import annotations

import math
from typing import Any

from config import get_settings

settings = get_settings()


def compute_candidate_score(
    compound: dict[str, Any],
    activities: list[dict[str, Any]],
    degree_in_graph: int = 1,
) -> dict[str, Any]:
    """
    Compute a composite, degree-penalized score for a compound candidate.

    Returns:
        score_report: dict with composite_score, sub_scores, ooc_flag, citations
    """
    # ── 1. Bioactivity Score (pChEMBL → 0-1) ─────────────────────────────
    pchembl_values = [
        float(a["pchembl_value"])
        for a in activities
        if a.get("pchembl_value") is not None
    ]
    if pchembl_values:
        avg_pchembl   = sum(pchembl_values) / len(pchembl_values)
        best_pchembl  = max(pchembl_values)
        # pChEMBL range is typically 3-12; normalize to [0,1]
        bioactivity_score = min(1.0, max(0.0, (best_pchembl - 3.0) / 9.0))
    else:
        avg_pchembl = best_pchembl = 0.0
        bioactivity_score = 0.0

    # ── 2. Selectivity Score (proxy: fewer targets = more selective) ───────
    # Count distinct targets in activity list
    unique_targets    = len({a.get("target_chembl_id") for a in activities if a.get("target_chembl_id")})
    selectivity_score = 1.0 / (1.0 + math.log1p(unique_targets))  # [0,1], higher = more selective

    # ── 3. Degree-Penalty Factor (hub-node suppression) ───────────────────
    # High-degree nodes in the KG are penalized to prevent topology bias
    degree_penalty = 1.0 / (1.0 + math.log1p(max(0, degree_in_graph - 1)))

    # ── 4. Drug-likeness Score (Lipinski Ro5 proxy) ────────────────────────
    mw    = float(compound.get("molecular_weight") or 500)
    alogp = float(compound.get("alogp") or 5)
    hbd   = float(compound.get("hbd") or 5)
    hba   = float(compound.get("hba") or 10)

    ro5_score = 1.0
    if mw    > 500: ro5_score -= 0.25
    if alogp > 5:   ro5_score -= 0.25
    if hbd   > 5:   ro5_score -= 0.25
    if hba   > 10:  ro5_score -= 0.25
    ro5_score = max(0.0, ro5_score)

    # ── 5. Composite Score ────────────────────────────────────────────────
    composite = (
        0.40 * bioactivity_score
        + 0.25 * selectivity_score
        + 0.20 * ro5_score
        + 0.15 * degree_penalty     # rewards specific, non-promiscuous compounds
    )

    # ── 6. Organ-on-Chip (OoC) Eligibility Flag ───────────────────────────
    ooc_eligible = (
        mw < settings.ooc_flag_mw_max
        and selectivity_score >= settings.selectivity_score_threshold
    )

    # ── 7. Activity citations ─────────────────────────────────────────────
    citations = list({a.get("citation", "") for a in activities if a.get("citation")})[:5]

    return {
        "composite_score":  round(composite, 4),
        "sub_scores": {
            "bioactivity":    round(bioactivity_score, 4),
            "selectivity":    round(selectivity_score, 4),
            "drug_likeness":  round(ro5_score, 4),
            "degree_penalty": round(degree_penalty, 4),
        },
        "bioactivity_details": {
            "best_pchembl":   round(best_pchembl, 2),
            "avg_pchembl":    round(avg_pchembl, 2),
            "num_activities": len(activities),
            "unique_targets": unique_targets,
        },
        "ooc_eligible":    ooc_eligible,
        "ooc_reason": (
            f"MW={mw:.1f} Da < {settings.ooc_flag_mw_max} Da; "
            f"selectivity={selectivity_score:.2f} ≥ {settings.selectivity_score_threshold}"
            if ooc_eligible
            else f"MW={mw:.1f} Da or selectivity={selectivity_score:.2f} does not meet OoC criteria"
        ),
        "citations": citations,
    }


def rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort candidates by composite_score descending and add rank field."""
    ranked = sorted(candidates, key=lambda c: c.get("composite_score", 0), reverse=True)
    for i, c in enumerate(ranked):
        c["rank"] = i + 1
    return ranked
