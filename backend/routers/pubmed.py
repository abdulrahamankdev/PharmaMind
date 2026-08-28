"""
/api/pubmed — PubMed literature search passthrough endpoints.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Query
from services import pubmed_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search")
async def search_literature(
    disease: str = Query("", description="Disease name (MeSH term)"),
    target: str  = Query("", description="Target gene symbol"),
    max_results: int = Query(10, ge=1, le=30),
):
    """Search PubMed for Disease + Target literature with abstracts."""
    parts = []
    if disease: parts.append(f"{disease}")
    if target:  parts.append(f"{target}[Gene]")
    parts.append("drug therapy")
    query = " AND ".join(parts)

    if not query.strip() or query == "drug therapy":
        return {"query": query, "articles": [], "error": "Please provide at least a disease or target."}

    try:
        articles = await pubmed_service.search_pubmed(query, max_results)
        return {
            "query": query,
            "articles": articles,
            "count": len(articles),
        }
    except Exception as e:
        logger.error("PubMed search error: %s", e)
        return {"query": query, "articles": [], "error": str(e)}


@router.get("/abstracts")
async def get_abstracts(
    pmids: str = Query(..., description="Comma-separated PMIDs"),
):
    """Fetch full abstracts for specific PMIDs."""
    pmid_list = [p.strip() for p in pmids.split(",") if p.strip()]
    if not pmid_list:
        return {"articles": [], "error": "No valid PMIDs provided"}
    try:
        from services.pubmed_service import _efetch
        articles = await _efetch(pmid_list)
        return {"pmids": pmid_list, "articles": articles}
    except Exception as e:
        return {"pmids": pmid_list, "articles": [], "error": str(e)}
