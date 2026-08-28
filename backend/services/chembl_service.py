"""
ChEMBL Service — retrieves validated bioactivity data via ChEMBL REST API.
No API key required. Uses the public EBI endpoint.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL = settings.chembl_api_base
TIMEOUT = 20.0


async def search_activities_by_target(
    target_chembl_id: str,
    activity_type: str = "IC50",
    limit: int = 25,
) -> list[dict[str, Any]]:
    """
    Fetch IC50 (or other) bioactivity records for a given ChEMBL target ID.
    Returns list of activity records with compound SMILES, pChEMBL, source DOI.
    """
    url = f"{BASE_URL}/activity.json"
    params = {
        "target_chembl_id": target_chembl_id,
        "standard_type": activity_type,
        "limit": limit,
        "offset": 0,
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    activities = data.get("activities", [])
    return [
        {
            "molecule_chembl_id": a.get("molecule_chembl_id"),
            "compound_name":      a.get("molecule_pref_name"),
            "smiles":             a.get("canonical_smiles"),
            "standard_value":     a.get("standard_value"),
            "standard_units":     a.get("standard_units"),
            "activity_type":      a.get("standard_type"),
            "pchembl_value":      a.get("pchembl_value"),
            "target_chembl_id":   a.get("target_chembl_id"),
            "target_name":        a.get("target_pref_name"),
            "assay_chembl_id":    a.get("assay_chembl_id"),
            "document_chembl_id": a.get("document_chembl_id"),
            "year":               a.get("year"),
            "citation": (
                f"ChEMBL Activity {a.get('activity_id')} | "
                f"Document: {a.get('document_chembl_id')} | "
                f"Assay: {a.get('assay_chembl_id')}"
            ),
        }
        for a in activities
    ]


async def search_target_by_gene(gene_symbol: str, limit: int = 5) -> list[dict]:
    """Search ChEMBL targets by gene symbol."""
    url = f"{BASE_URL}/target.json"
    params = {"target_synonym__icontains": gene_symbol, "limit": limit, "format": "json"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    targets = data.get("targets", [])
    return [
        {
            "target_chembl_id":  t.get("target_chembl_id"),
            "pref_name":         t.get("pref_name"),
            "target_type":       t.get("target_type"),
            "organism":          t.get("organism"),
            "gene_symbol":       gene_symbol,
        }
        for t in targets
    ]


async def get_compound_details(molecule_chembl_id: str) -> dict:
    """Fetch detailed compound data by ChEMBL molecule ID."""
    url = f"{BASE_URL}/molecule/{molecule_chembl_id}.json"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

    props = data.get("molecule_properties", {}) or {}
    return {
        "molecule_chembl_id": data.get("molecule_chembl_id"),
        "pref_name":          data.get("pref_name"),
        "smiles":             data.get("molecule_structures", {}).get("canonical_smiles"),
        "inchi_key":          data.get("molecule_structures", {}).get("standard_inchi_key"),
        "molecular_weight":   props.get("full_mwt"),
        "alogp":              props.get("alogp"),
        "hbd":                props.get("hbd"),
        "hba":                props.get("hba"),
        "psa":                props.get("psa"),
        "ro5_violations":     props.get("num_ro5_violations"),
        "max_phase":          data.get("max_phase"),
        "citation":           f"ChEMBL Compound {molecule_chembl_id}",
    }
