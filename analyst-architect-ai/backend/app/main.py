import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from app.database import create_tables
from app.api.routers import documents, reviews, knowledge_base, memory, diagrams, audit
from app.api.routers import risk_catalog, lessons as lessons_router
from app.api.routers import settings as settings_router
from app.api.routers import auth as auth_router
from app.api.routers import build_projects, dashboard, seed
from app.api.deps import require_analyst, require_architect, require_admin

os.makedirs("data", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_tables()
    except Exception as e:
        print(f"Warning: create_tables failed ({e}), continuing...")
    # Seed default users on first start
    from app.database import AsyncSessionLocal
    from app.services.auth_service import seed_default_users
    async with AsyncSessionLocal() as db:
        await seed_default_users(db)
    yield


app = FastAPI(
    title="Analyst-Architect-AI",
    description=(
        "AI Copilot for System Analysts and Solution Architects — "
        "AI review, RAG knowledge base, ADR/URS/SRS/API/diagram generation, "
        "memory framework, audit center, and economic ROI evaluation for "
        "applications built through the platform."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve built frontend static files (CSS/JS/fonts)
_frontend_build = Path(__file__).resolve().parents[2] / "frontend" / "build"
if _frontend_build.is_dir():
    app.mount("/static", StaticFiles(directory=str(_frontend_build / "static")), name="static")

# Routers
# /auth/* is public (login) or self-protected per-endpoint (register/users = admin only)
app.include_router(auth_router.router)

# Business routers require a valid JWT for any of the three roles
# (admin | analyst | architect)
app.include_router(documents.router, dependencies=[Depends(require_analyst)])
app.include_router(reviews.router, dependencies=[Depends(require_analyst)])
app.include_router(knowledge_base.router, dependencies=[Depends(require_analyst)])
app.include_router(memory.router, dependencies=[Depends(require_analyst)])
app.include_router(diagrams.router, dependencies=[Depends(require_analyst)])
app.include_router(audit.router, dependencies=[Depends(require_analyst)])
app.include_router(dashboard.router, dependencies=[Depends(require_analyst)])
app.include_router(risk_catalog.router, dependencies=[Depends(require_analyst)])
app.include_router(lessons_router.router, dependencies=[Depends(require_analyst)])

# Economic module — any authenticated role can create/estimate,
# actuals entry (post-launch reconciliation) requires architect/admin judgement
app.include_router(build_projects.router, dependencies=[Depends(require_analyst)])

# Provider settings: architect or admin only (per Access Matrix)
app.include_router(settings_router.router, dependencies=[Depends(require_architect)])

# Seed/demo-data endpoints: admin only (bulk-inserts data, should be deliberate)
app.include_router(seed.router, dependencies=[Depends(require_admin)])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "Analyst-Architect-AI"}


@app.get("/")
async def root():
    return {
        "name": "Analyst-Architect-AI",
        "version": "1.0.0",
        "docs": "/docs",
    }
