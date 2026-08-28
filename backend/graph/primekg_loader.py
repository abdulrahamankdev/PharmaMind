"""
PrimeKG Loader — Loads a subset of PrimeKG into Neo4j via BioCypher.

PrimeKG (https://zitniklab.hms.harvard.edu/projects/PrimeKG/) is a precision
medicine knowledge graph with 20+ biomedical databases integrated.

This loader reads the local CSV subset in data/primekg_sample.csv and creates:
  - Disease nodes
  - Target (Gene/Protein) nodes
  - Compound (Drug) nodes
  - ASSOCIATED_WITH edges (Disease → Target)
  - MODULATED_BY edges (Target → Compound)

Usage: python backend/graph/primekg_loader.py
       OR called from scripts/init_graph.py
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys

# Ensure backend/ is on the path when running from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.neo4j_service import run_write_query, close_driver

logger = logging.getLogger(__name__)

SAMPLE_CSV = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "primekg_sample.csv"
)


async def create_constraints():
    """Create uniqueness constraints for node IDs."""
    constraints = [
        "CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE",
        "CREATE CONSTRAINT target_id IF NOT EXISTS FOR (t:Target) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT compound_id IF NOT EXISTS FOR (c:Compound) REQUIRE c.id IS UNIQUE",
    ]
    for c in constraints:
        try:
            await run_write_query(c)
            logger.info("Constraint: %s", c[:60])
        except Exception as e:
            logger.warning("Constraint already exists or failed: %s", e)


async def load_csv(path: str) -> list[dict]:
    """Load PrimeKG CSV rows. Expected columns: x_type, x_id, x_name, y_type, y_id, y_name, relation."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"PrimeKG sample CSV not found at: {path}\n"
            "Download instructions: see README.md → Data Setup"
        )
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from %s", len(rows), path)
    return rows


async def load_nodes(rows: list[dict]):
    """Merge all unique nodes from PrimeKG rows into Neo4j."""
    diseases:   dict[str, dict] = {}
    targets:    dict[str, dict] = {}
    compounds:  dict[str, dict] = {}

    for row in rows:
        for prefix in ("x", "y"):
            ntype = row.get(f"{prefix}_type", "").lower()
            nid   = row.get(f"{prefix}_id", "").strip()
            nname = row.get(f"{prefix}_name", "").strip()

            if not nid:
                continue
            if "disease" in ntype:
                diseases[nid] = {"id": nid, "name": nname}
            elif "gene" in ntype or "protein" in ntype:
                targets[nid] = {
                    "id":          nid,
                    "name":        nname,
                    "gene_symbol": nname.upper(),
                    "target_type": "SINGLE PROTEIN",
                }
            elif "drug" in ntype or "compound" in ntype:
                compounds[nid] = {"id": nid, "name": nname}

    # Batch upsert diseases
    if diseases:
        await run_write_query(
            """
            UNWIND $nodes AS n
            MERGE (d:Disease {id: n.id})
            SET d.name = n.name, d.degree = 0
            """,
            {"nodes": list(diseases.values())},
        )
        logger.info("Upserted %d Disease nodes", len(diseases))

    # Batch upsert targets
    if targets:
        await run_write_query(
            """
            UNWIND $nodes AS n
            MERGE (t:Target {id: n.id})
            SET t.name = n.name,
                t.gene_symbol = n.gene_symbol,
                t.target_type = n.target_type,
                t.degree = 0
            """,
            {"nodes": list(targets.values())},
        )
        logger.info("Upserted %d Target nodes", len(targets))

    # Batch upsert compounds
    if compounds:
        await run_write_query(
            """
            UNWIND $nodes AS n
            MERGE (c:Compound {id: n.id})
            SET c.name = n.name, c.degree = 0
            """,
            {"nodes": list(compounds.values())},
        )
        logger.info("Upserted %d Compound nodes", len(compounds))


async def load_edges(rows: list[dict]):
    """Create relationships from PrimeKG edges."""
    disease_target = []
    target_compound = []

    for row in rows:
        xtype = row.get("x_type", "").lower()
        ytype = row.get("y_type", "").lower()
        xid   = row.get("x_id", "").strip()
        yid   = row.get("y_id", "").strip()
        rel   = row.get("relation", "ASSOCIATED").upper().replace(" ", "_")

        if not (xid and yid):
            continue

        if "disease" in xtype and ("gene" in ytype or "protein" in ytype):
            disease_target.append({"disease_id": xid, "target_id": yid, "relation": rel})
        elif ("gene" in xtype or "protein" in xtype) and ("drug" in ytype or "compound" in ytype):
            target_compound.append({"target_id": xid, "compound_id": yid, "relation": rel})
        elif "disease" in ytype and ("gene" in xtype or "protein" in xtype):
            disease_target.append({"disease_id": yid, "target_id": xid, "relation": rel})
        elif ("drug" in xtype or "compound" in xtype) and ("gene" in ytype or "protein" in ytype):
            target_compound.append({"target_id": yid, "compound_id": xid, "relation": rel})

    if disease_target:
        await run_write_query(
            """
            UNWIND $rels AS r
            MATCH (d:Disease {id: r.disease_id})
            MATCH (t:Target  {id: r.target_id})
            MERGE (d)-[:ASSOCIATED_WITH]->(t)
            """,
            {"rels": disease_target},
        )
        logger.info("Created %d Disease→Target edges", len(disease_target))

    if target_compound:
        await run_write_query(
            """
            UNWIND $rels AS r
            MATCH (t:Target   {id: r.target_id})
            MATCH (c:Compound {id: r.compound_id})
            MERGE (t)-[:MODULATED_BY]->(c)
            """,
            {"rels": target_compound},
        )
        logger.info("Created %d Target→Compound edges", len(target_compound))


async def update_degrees():
    """Update degree property on all nodes (used for degree-agnostic scoring)."""
    await run_write_query("""
        MATCH (n)
        OPTIONAL MATCH (n)-[r]-()
        WITH n, count(r) AS deg
        SET n.degree = deg
    """)
    logger.info("Updated degree properties on all nodes")


async def run_loader():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Starting PrimeKG loader...")

    await create_constraints()
    rows = await load_csv(SAMPLE_CSV)
    await load_nodes(rows)
    await load_edges(rows)
    await update_degrees()
    await close_driver()

    logger.info("✅ PrimeKG loading complete!")


if __name__ == "__main__":
    asyncio.run(run_loader())
