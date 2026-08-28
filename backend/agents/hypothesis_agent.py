"""
Hypothesis Agent — Primary AI agent that generates structured drug discovery hypotheses.

Given a disease, target, and optional compound context, generates a JSON hypothesis
with mechanistic reasoning, predicted efficacy rationale, and full source citations.
"""
from __future__ import annotations

import logging
from typing import Any

from services.ollama_service import generate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior computational drug discovery scientist.
Your task is to generate rigorous, mechanistically grounded drug discovery hypotheses.
You MUST respond with ONLY valid JSON. Do not include any prose outside the JSON object.
Every mechanistic claim MUST include at least one citation from the provided evidence.
Never hallucinate citations — only use what is explicitly provided in the context.

DISCLAIMER: This is a research hypothesis for scientific exploration only.
It does not constitute medical advice or clinical decision-making."""


def _build_prompt(
    disease: str,
    target: str,
    compound: str | None,
    kg_context: list[dict],
    chembl_context: list[dict],
    pubmed_context: list[dict],
) -> str:
    chembl_str = "\n".join(
        f"  - {a.get('compound_name','?')} | IC50={a.get('standard_value','?')} {a.get('standard_units','nM')} "
        f"| pChEMBL={a.get('pchembl_value','?')} | {a.get('citation','')}"
        for a in chembl_context[:10]
    )
    pubmed_str = "\n".join(
        f"  - [{a.get('pmid','?')}] {a.get('title','?')} | {a.get('citation','')}"
        for a in pubmed_context[:8]
    )
    kg_str = "\n".join(
        f"  - {node.get('label','?')} ({node.get('type','?')})"
        for node in kg_context[:15]
    )

    return f"""
Generate a drug discovery hypothesis for the following research context.
Respond ONLY with a JSON object matching the schema below.

## Research Context
- Disease:  {disease}
- Target:   {target}
- Compound: {compound or "Not specified — evaluate top candidates from evidence"}

## Knowledge Graph Context (Disease ↔ Target ↔ Compound nodes)
{kg_str or "  No KG data available."}

## ChEMBL Bioactivity Evidence
{chembl_str or "  No ChEMBL data available."}

## PubMed Literature Evidence
{pubmed_str or "  No PubMed data available."}

## Required JSON Schema
{{
  "hypothesis_id": "<unique string, e.g. HYP-001>",
  "disease": "<disease name>",
  "target": "<target/gene name>",
  "proposed_compound": "<compound name or ChEMBL ID>",
  "mechanism_of_action": "<mechanistic explanation, 2-4 sentences>",
  "predicted_efficacy": {{
    "rationale": "<evidence-based rationale>",
    "confidence_level": "<high|medium|low>",
    "supporting_ic50_nm": <best IC50 value in nM or null>,
    "best_pchembl": <pChEMBL value or null>
  }},
  "biological_pathway": "<primary pathway involved>",
  "drug_likeness_assessment": "<Lipinski Ro5 assessment>",
  "knowledge_gaps": ["<gap 1>", "<gap 2>"],
  "citations": [
    {{
      "source_type": "<ChEMBL|PubMed|KnowledgeGraph>",
      "id": "<PMID or ChEMBL ID>",
      "claim": "<exact claim this citation supports>",
      "full_citation": "<formatted citation string>"
    }}
  ],
  "disclaimer": "This hypothesis is generated for exploratory research purposes only. It does not constitute medical advice.",
  "confidence_flags": {{
    "has_experimental_ic50": <true|false>,
    "has_pubmed_evidence": <true|false>,
    "has_kg_pathway_support": <true|false>,
    "recommended_for_ooc_validation": <true|false>
  }}
}}
"""


async def generate_hypothesis(
    disease: str,
    target: str,
    compound: str | None = None,
    kg_context: list[dict] | None = None,
    chembl_context: list[dict] | None = None,
    pubmed_context: list[dict] | None = None,
) -> dict[str, Any]:
    """Generate a structured drug discovery hypothesis using local Ollama LLM."""
    prompt = _build_prompt(
        disease=disease,
        target=target,
        compound=compound,
        kg_context=kg_context or [],
        chembl_context=chembl_context or [],
        pubmed_context=pubmed_context or [],
    )

    logger.info("Hypothesis agent generating for disease=%s target=%s", disease, target)
    result = await generate(prompt, system_prompt=SYSTEM_PROMPT, expect_json=True)

    # Ensure disclaimer is always present
    if isinstance(result, dict):
        result.setdefault(
            "disclaimer",
            "This hypothesis is generated for exploratory research purposes only. "
            "It does not constitute medical advice.",
        )
    return result
