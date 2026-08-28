"""
PubMed Service — fetches scientific literature via NCBI E-utilities.
Uses ESearch to find PMIDs then EFetch to retrieve abstracts.
No API key needed for low-volume queries (<3 req/s).
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BASE_URL  = settings.pubmed_api_base
EMAIL     = settings.pubmed_email
TIMEOUT   = 20.0


async def search_pubmed(
    query: str, max_results: int = 10
) -> list[dict[str, Any]]:
    """
    Search PubMed and return article metadata with abstracts.
    Full pipeline: ESearch → PMIDs → EFetch → parsed articles.
    """
    pmids = await _esearch(query, max_results)
    if not pmids:
        return []
    articles = await _efetch(pmids)
    return articles


async def _esearch(query: str, retmax: int) -> list[str]:
    """Run ESearch and return list of PMIDs."""
    url = f"{BASE_URL}/esearch.fcgi"
    params = {
        "db":      "pubmed",
        "term":    query,
        "retmax":  retmax,
        "retmode": "json",
        "email":   EMAIL,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    return data.get("esearchresult", {}).get("idlist", [])


async def _efetch(pmids: list[str]) -> list[dict[str, Any]]:
    """Fetch full article records for given PMIDs (XML → dict)."""
    url = f"{BASE_URL}/efetch.fcgi"
    params = {
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
        "email":   EMAIL,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        xml_text = resp.text

    return _parse_pubmed_xml(xml_text)


def _parse_pubmed_xml(xml_text: str) -> list[dict[str, Any]]:
    """Parse PubMed XML into structured article dicts."""
    articles = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error(f"PubMed XML parse error: {e}")
        return []

    for article in root.findall(".//PubmedArticle"):
        try:
            pmid_el   = article.find(".//PMID")
            title_el  = article.find(".//ArticleTitle")
            abstract_els = article.findall(".//AbstractText")
            journal_el = article.find(".//Journal/Title")
            year_el    = article.find(".//PubDate/Year")

            # Authors
            authors = []
            for author in article.findall(".//Author"):
                last  = author.findtext("LastName", "")
                first = author.findtext("ForeName", "")
                if last:
                    authors.append(f"{last} {first}".strip())

            pmid     = pmid_el.text if pmid_el is not None else "N/A"
            title    = title_el.text if title_el is not None else "N/A"
            abstract = " ".join(el.text or "" for el in abstract_els)
            journal  = journal_el.text if journal_el is not None else "N/A"
            year     = year_el.text if year_el is not None else "N/A"

            articles.append(
                {
                    "pmid":     pmid,
                    "title":    title,
                    "abstract": abstract[:1200],  # Truncate to keep payload manageable
                    "authors":  authors[:5],
                    "journal":  journal,
                    "year":     year,
                    "citation": (
                        f"{', '.join(authors[:3])}{'...' if len(authors)>3 else ''} "
                        f"({year}). {title}. {journal}. PMID: {pmid}."
                    ),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )
        except Exception as e:
            logger.warning(f"Failed to parse article: {e}")
            continue

    return articles
