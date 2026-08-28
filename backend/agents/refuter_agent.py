"""
Refuter Agent — Adversarial secondary AI agent that aggressively challenges hypotheses.

Uses ChEMBL bioactivity data, selectivity profiles, and off-target evidence
to identify flaws, false-positive risks, and experimental limitations
in the primary hypothesis agent's output.
"""
from __future__ import annotations

import logging
from typing import Any

from services.ollama_service import generate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an adversarial computational pharmacologist acting as a critical reviewer.
Your SOLE JOB is to rigorously challenge drug discovery hypotheses and identify false positives.
You are skeptical, evidence-driven, and do NOT accept claims without bioactivity support.

CRITICAL RULES:
1. Respond ONLY with valid JSON — no prose outside the JSON.
2. Every refutation point MUST cite specific evidence (IC50 values, PMIDs, or assay data).
3. Flag off-target activity, poor selectivity, ADMET concerns, and assay artifacts.
4. Mark candidates as LIKELY_FALSE_POSITIVE if IC50 > 10,000 nM or pChEMBL < 4.0.
5. Recommend specific experimental validation steps to resolve ambiguities.

DISCLAIMER: This is adversarial analysis for research purposes. Not medical advice."""


def _build_refutation_prompt(
    hypothesis: dict[str, Any],
    chembl_activities: list[dict[str, Any]],
    off_target_activities: list[dict[str, Any]],
) -> str:
    hyp_json = str(hypothesis)[:2000]  # Truncate to stay within context

    activity_str = "\n".join(
        f"  - {a.get('compound_name','?')} vs {a.get('target_name','?')}: "
        f"IC50={a.get('standard_value','?')} {a.get('standard_units','nM')}, "
        f"pChEMBL={a.get('pchembl_value','?')}, Assay={a.get('assay_chembl_id','?')}"
        for a in chembl_activities[:12]
    )
    off_target_str = "\n".join(
        f"  - {a.get('compound_name','?')} vs {a.get('target_name','?')}: "
        f"IC50={a.get('standard_value','?')} {a.get('standard_units','nM')}"
        for a in off_target_activities[:8]
    )

    return f"""
You are reviewing the following drug discovery hypothesis. Aggressively challenge it.

## Hypothesis Under Review
{hyp_json}

## Available ChEMBL Activity Data for Proposed Compound
{activity_str or "  No activity data available — treat as INSUFFICIENT EVIDENCE."}

## Potential Off-Target Activity Data
{off_target_str or "  No off-target data found."}

## Required JSON Schema for Refutation
{{
  "refutation_id": "<string, e.g. REF-001>",
  "hypothesis_id": "<hypothesis_id from input>",
  "overall_verdict": "<SUPPORTED|PARTIALLY_SUPPORTED|REFUTED|INSUFFICIENT_EVIDENCE>",
  "confidence_in_verdict": "<high|medium|low>",
  "false_positive_risk": "<high|medium|low>",
  "refutation_points": [
    {{
      "point_id": "<RP-1, RP-2, ...>",
      "category": "<selectivity|off_target|admet|assay_artifact|insufficient_evidence|mechanism_flaw>",
      "severity": "<critical|major|minor>",
      "claim": "<specific flaw or concern identified>",
      "evidence": "<IC50 values, pChEMBL, assay IDs, or PMID cited>",
      "citation": "<formatted citation>"
    }}
  ],
  "off_target_risks": [
    {{
      "off_target": "<target name>",
      "ic50_nm": <value or null>,
      "selectivity_ratio": <primary_IC50 / off_target_IC50 or null>,
      "clinical_significance": "<explanation>"
    }}
  ],
  "admet_concerns": [
    "<ADMET concern 1>",
    "<ADMET concern 2>"
  ],
  "recommended_experiments": [
    {{
      "experiment_type": "<e.g., kinase selectivity panel, ADMET assay, in vivo PK>",
      "rationale": "<why this experiment is needed>",
      "ooc_applicable": <true|false>,
      "ooc_rationale": "<why organ-on-chip would help, if applicable>"
    }}
  ],
  "final_recommendation": "<PROCEED|PROCEED_WITH_CAUTION|DO_NOT_PROCEED>",
  "summary": "<2-3 sentence summary of refutation findings>",
  "citations": [
    {{
      "source_type": "<ChEMBL|PubMed|Inference>",
      "id": "<ID>",
      "claim": "<claim this citation supports>",
      "full_citation": "<formatted citation string>"
    }}
  ],
  "disclaimer": "This adversarial analysis is for research purposes only. Not medical advice."
}}
"""


async def refute_hypothesis(
    hypothesis: dict[str, Any],
    chembl_activities: list[dict[str, Any]] | None = None,
    off_target_activities: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Run adversarial refutation against a primary hypothesis.
    Returns structured JSON with verdict, refutation points, and experiment recommendations.
    """
    prompt = _build_refutation_prompt(
        hypothesis=hypothesis,
        chembl_activities=chembl_activities or [],
        off_target_activities=off_target_activities or [],
    )

    logger.info(
        "Refuter agent challenging hypothesis_id=%s",
        hypothesis.get("hypothesis_id", "unknown"),
    )
    result = await generate(prompt, system_prompt=SYSTEM_PROMPT, expect_json=True)

    if isinstance(result, dict):
        result.setdefault(
            "disclaimer",
            "This adversarial analysis is for research purposes only. Not medical advice.",
        )
        result.setdefault("hypothesis_id", hypothesis.get("hypothesis_id", "unknown"))

    return result
