"""
Neo4j Service — manages driver lifecycle and Cypher query helpers.
Uses async context manager for clean session management.
Includes a robust in-memory CSV fallback when Neo4j is unavailable.
"""
from __future__ import annotations

import logging
import csv
import os
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_driver: AsyncDriver | None = None
_fallback_instance: LocalGraphFallback | None = None

class LocalGraphFallback:
    def __init__(self):
        self.nodes = {}       # id -> {"id", "name", "gene_symbol", "target_type", "type", "degree"}
        self.edges = []       # list of {"source", "target", "type"}
        self.load_graph()

    def load_graph(self):
        csv_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "primekg_sample.csv"
        ))
        if not os.path.exists(csv_path):
            logger.error("Fallback CSV not found at: %s", csv_path)
            return

        rows = []
        try:
            with open(csv_path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
        except Exception as e:
            logger.error("Failed to read fallback CSV: %s", e)
            return

        # Build all nodes
        for row in rows:
            for prefix in ("x", "y"):
                ntype = row.get(f"{prefix}_type", "").lower()
                nid   = row.get(f"{prefix}_id", "").strip()
                nname = row.get(f"{prefix}_name", "").strip()
                if not nid:
                    continue

                if "disease" in ntype:
                    mapped_type = "Disease"
                elif "gene" in ntype or "protein" in ntype:
                    mapped_type = "Target"
                elif "drug" in ntype or "compound" in ntype:
                    mapped_type = "Compound"
                else:
                    mapped_type = "Other"

                if nid not in self.nodes:
                    self.nodes[nid] = {
                        "id": nid,
                        "name": nname,
                        "gene_symbol": nname.upper(),
                        "target_type": "SINGLE PROTEIN",
                        "type": mapped_type,
                        "degree": 0,
                    }

        # Create unique edges
        seen_edges = set()
        for row in rows:
            xtype = row.get("x_type", "").lower()
            ytype = row.get("y_type", "").lower()
            xid   = row.get("x_id", "").strip()
            yid   = row.get("y_id", "").strip()
            if not (xid and yid):
                continue

            edge = None
            if "disease" in xtype and ("gene" in ytype or "protein" in ytype):
                edge = {"source": xid, "target": yid, "type": "ASSOCIATED_WITH"}
            elif ("gene" in xtype or "protein" in xtype) and ("drug" in ytype or "compound" in ytype):
                edge = {"source": xid, "target": yid, "type": "MODULATED_BY"}
            elif "disease" in ytype and ("gene" in xtype or "protein" in xtype):
                edge = {"source": yid, "target": xid, "type": "ASSOCIATED_WITH"}
            elif ("drug" in xtype or "compound" in xtype) and ("gene" in ytype or "protein" in ytype):
                edge = {"source": yid, "target": xid, "type": "MODULATED_BY"}

            if edge:
                edge_key = (edge["source"], edge["target"], edge["type"])
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    self.edges.append(edge)

        # Count degrees based on valid edges
        degrees = {}
        for edge in self.edges:
            degrees[edge["source"]] = degrees.get(edge["source"], 0) + 1
            degrees[edge["target"]] = degrees.get(edge["target"], 0) + 1

        for nid, deg in degrees.items():
            if nid in self.nodes:
                self.nodes[nid]["degree"] = deg

        logger.info(
            "Local CSV graph loaded. Nodes: %d, Edges: %d",
            len(self.nodes),
            len(self.edges),
        )

    def find_disease_targets(self, disease_name: str, limit: int = 20) -> list[dict]:
        disease_name_lower = disease_name.lower()
        # Find matching diseases
        matching_diseases = [
            n for n in self.nodes.values()
            if n["type"] == "Disease" and disease_name_lower in n["name"].lower()
        ]
        
        results = []
        for d in matching_diseases:
            # Find targets connected to d
            target_ids = [
                e["target"] for e in self.edges
                if e["source"] == d["id"] and e["type"] == "ASSOCIATED_WITH"
            ]
            for tid in target_ids:
                t = self.nodes.get(tid)
                if t and t["type"] == "Target":
                    norm_score = 1.0 / (1.0 + t["degree"])
                    results.append({
                        "target_id": t["id"],
                        "target_name": t["name"],
                        "gene_symbol": t["gene_symbol"],
                        "target_type": t["target_type"],
                        "disease_name": d["name"],
                        "association_count": 1,
                        "norm_score": round(norm_score, 4),
                    })
        results.sort(key=lambda x: x["norm_score"], reverse=True)
        return results[:limit]

    def find_target_compounds(self, target_id: str, limit: int = 20) -> list[dict]:
        t = self.nodes.get(target_id)
        if not t:
            return []
        
        # Find compounds connected to this target
        comp_ids = [
            e["target"] for e in self.edges
            if e["source"] == target_id and e["type"] == "MODULATED_BY"
        ]
        
        results = []
        for cid in comp_ids:
            c = self.nodes.get(cid)
            if c and c["type"] == "Compound":
                results.append({
                    "compound_id": c["id"],
                    "compound_name": c["name"],
                    "smiles": None,
                    "molecular_weight": 400.0, # fallback default for Lipinski check
                    "inchi_key": None,
                    "target_name": t["name"],
                    "pchembl": 6.5, # moderate fallback default
                    "activity_type": "IC50",
                    "ooc_eligible": True,
                })
        return results[:limit]

    def get_graph_subgraph(self, disease_name: str, depth: int = 2) -> dict[str, list[dict]]:
        disease_name_lower = disease_name.lower()
        matching_diseases = [
            n for n in self.nodes.values()
            if n["type"] == "Disease" and disease_name_lower in n["name"].lower()
        ]
        if not matching_diseases:
            return {"nodes": [], "edges": []}
            
        # We build subgraph from matching disease nodes, their associated targets, and modulates compounds
        sub_nodes = {}
        sub_edges = []
        
        for d in matching_diseases:
            sub_nodes[d["id"]] = {"id": d["id"], "label": d["name"], "type": "Disease"}
            
            # Find targets
            targets_edges = [
                e for e in self.edges
                if e["source"] == d["id"] and e["type"] == "ASSOCIATED_WITH"
            ]
            for e in targets_edges:
                tid = e["target"]
                t = self.nodes.get(tid)
                if t:
                    sub_nodes[tid] = {"id": tid, "label": t["name"], "type": "Target"}
                    sub_edges.append({"source": d["id"], "target": tid, "type": "ASSOCIATED_WITH"})
                    
                    # Find compounds for this target
                    comp_edges = [
                        ce for ce in self.edges
                        if ce["source"] == tid and ce["type"] == "MODULATED_BY"
                    ]
                    for ce in comp_edges:
                        cid = ce["target"]
                        c = self.nodes.get(cid)
                        if c:
                            sub_nodes[cid] = {"id": cid, "label": c["name"], "type": "Compound"}
                            sub_edges.append({"source": tid, "target": cid, "type": "MODULATED_BY"})
                            
        return {
            "nodes": list(sub_nodes.values()),
            "edges": sub_edges,
        }

    def search_nodes(self, query_text: str, limit: int = 10) -> list[dict]:
        q = query_text.lower()
        results = []
        for n in self.nodes.values():
            if q in n["name"].lower() or (n["type"] == "Target" and q in n["gene_symbol"].lower()):
                results.append({
                    "id": n["id"],
                    "name": n["name"],
                    "type": n["type"],
                })
        return results[:limit]


def get_fallback() -> LocalGraphFallback:
    global _fallback_instance
    if _fallback_instance is None:
        _fallback_instance = LocalGraphFallback()
    return _fallback_instance


async def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver():
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


async def run_query(cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a Cypher read query and return list of record dicts."""
    try:
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records
    except Exception as e:
        logger.warning("Neo4j database query failed, falling back to local memory: %s", e)
        raise ConnectionError("Neo4j unreachable")


async def run_write_query(cypher: str, params: dict | None = None) -> list[dict[str, Any]]:
    """Execute a Cypher write query inside a transaction."""
    try:
        driver = await get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records
    except Exception as e:
        logger.warning("Neo4j database write failed, falling back to local memory: %s", e)
        raise ConnectionError("Neo4j unreachable")


# ── Domain-specific Queries (with Fallbacks) ────────────────────────────────

async def find_disease_targets(disease_name: str, limit: int = 20) -> list[dict]:
    """Return targets associated with a disease, with degree-normalized score."""
    try:
        cypher = """
        MATCH (d:Disease)-[r:ASSOCIATED_WITH]->(t:Target)
        WHERE toLower(d.name) CONTAINS toLower($disease_name)
        WITH t, count(r) AS association_count,
             d.name AS disease_name
        // Degree-agnostic normalization: penalize high-degree hub nodes
        WITH t, disease_name, association_count,
             toFloat(association_count) / (1.0 + toFloat(t.degree)) AS norm_score
        RETURN
            t.id          AS target_id,
            t.name        AS target_name,
            t.gene_symbol AS gene_symbol,
            t.target_type AS target_type,
            disease_name,
            association_count,
            norm_score
        ORDER BY norm_score DESC
        LIMIT $limit
        """
        return await run_query(cypher, {"disease_name": disease_name, "limit": limit})
    except Exception:
        logger.info("Using local graph fallback for find_disease_targets")
        return get_fallback().find_disease_targets(disease_name, limit)


async def find_target_compounds(target_id: str, limit: int = 20) -> list[dict]:
    """Return compounds known to modulate a target."""
    try:
        cypher = """
        MATCH (t:Target {id: $target_id})-[r:MODULATED_BY]->(c:Compound)
        WITH c, t, r,
             toFloat(r.pchembl_value) AS pchembl,
             toFloat(c.molecular_weight) AS mw
        RETURN
            c.id               AS compound_id,
            c.name             AS compound_name,
            c.smiles           AS smiles,
            c.molecular_weight AS molecular_weight,
            c.inchi_key        AS inchi_key,
            t.name             AS target_name,
            pchembl,
            r.activity_type    AS activity_type,
            CASE WHEN mw < 500 THEN true ELSE false END AS ooc_eligible
        ORDER BY pchembl DESC
        LIMIT $limit
        """
        return await run_query(cypher, {"target_id": target_id, "limit": limit})
    except Exception:
        logger.info("Using local graph fallback for find_target_compounds")
        return get_fallback().find_target_compounds(target_id, limit)


async def get_graph_subgraph(
    disease_name: str, depth: int = 2
) -> dict[str, list[dict]]:
    """Return nodes and edges for D3 visualization."""
    try:
        cypher = """
        MATCH path = (d:Disease)-[:ASSOCIATED_WITH*1..2]->(t:Target)-[:MODULATED_BY]->(c:Compound)
        WHERE toLower(d.name) CONTAINS toLower($disease_name)
        WITH nodes(path) AS ns, relationships(path) AS rels
        UNWIND ns AS n
        WITH DISTINCT n, rels
        RETURN
            collect(DISTINCT {
                id:    coalesce(n.id, toString(id(n))),
                label: coalesce(n.name, n.id),
                type:  labels(n)[0]
            }) AS nodes,
            [r IN rels | {
                source: coalesce(startNode(r).id, toString(id(startNode(r)))),
                target: coalesce(endNode(r).id,   toString(id(endNode(r)))),
                type:   type(r)
            }] AS edges
        LIMIT 1
        """
        results = await run_query(cypher, {"disease_name": disease_name})
        if results:
            return results[0]
        return {"nodes": [], "edges": []}
    except Exception:
        logger.info("Using local graph fallback for get_graph_subgraph")
        return get_fallback().get_graph_subgraph(disease_name, depth)


async def search_nodes(query_text: str, limit: int = 10) -> list[dict]:
    """Full-text node search across Disease, Target, Compound."""
    try:
        cypher = """
        CALL {
            MATCH (d:Disease)
            WHERE toLower(d.name) CONTAINS toLower($q)
            RETURN d.id AS id, d.name AS name, 'Disease' AS type
            UNION
            MATCH (t:Target)
            WHERE toLower(t.name) CONTAINS toLower($q) OR toLower(t.gene_symbol) CONTAINS toLower($q)
            RETURN t.id AS id, t.name AS name, 'Target' AS type
            UNION
            MATCH (c:Compound)
            WHERE toLower(c.name) CONTAINS toLower($q)
            RETURN c.id AS id, c.name AS name, 'Compound' AS type
        }
        RETURN id, name, type LIMIT $limit
        """
        return await run_query(cypher, {"q": query_text, "limit": limit})
    except Exception:
        logger.info("Using local graph fallback for search_nodes")
        return get_fallback().search_nodes(query_text, limit)
