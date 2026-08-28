import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from routers import query, graph, chembl, pubmed, validate

settings = get_settings()

# ── App Initialization ─────────────────────────────────────────────────────
app = FastAPI(
    title="PharmaMind MVP API",
    description=(
        "Adversarial, evidence-grounded drug discovery research assistant. "
        "Ranks Disease → Target → Compound hypotheses using Knowledge Graphs, "
        "ChEMBL bioactivity data, PubMed literature, and local Ollama AI agents. "
        "\n\n⚠️  **DISCLAIMER:** This system is an exploratory research-support tool. "
        "It does NOT make medical decisions and must NOT be used for clinical purposes."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(query.router,    prefix="/api/query",    tags=["Research Query"])
app.include_router(graph.router,    prefix="/api/graph",    tags=["Knowledge Graph"])
app.include_router(chembl.router,   prefix="/api/chembl",   tags=["ChEMBL Bioactivity"])
app.include_router(pubmed.router,   prefix="/api/pubmed",   tags=["PubMed Literature"])
app.include_router(validate.router, prefix="/api/validate", tags=["Adversarial Validation"])

# ── Serve Frontend ─────────────────────────────────────────────────────────
# Frontend available at http://localhost:8000/app/
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/app", StaticFiles(directory=_frontend_dir, html=True), name="frontend")


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "operational",
        "service": "PharmaMind MVP",
        "version": "0.1.0",
        "disclaimer": (
            "This is an exploratory research-support tool. "
            "It does not make medical or clinical decisions."
        ),
    }


@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse({"status": "healthy"})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level="info",
    )
