# Refactored FastAPI application entrypoint (conditional /api prefix)
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import origins, APP_ENV
from app.deps import get_db
import crud
from app.services.prompt_service import _seed_prompt_functions_logic

# Routers
from app.routers.auth_routes import router as auth_router
from app.routers.rfp_routes import router as rfp_router
from app.routers.kb_routes import router as kb_router
from app.routers.prompt_functions_routes import router as prompt_router
from app.api.routes_examples import router as examples_router
from app.api.routes_sections import router as sections_router

# Use /api in production/staging, no prefix in development (local)
API_PREFIX = "/api" if (APP_ENV or "development").lower() != "development" else ""

app = FastAPI(title="RFP RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers w/ conditional prefix
app.include_router(auth_router,     prefix=API_PREFIX)
app.include_router(rfp_router,      prefix=API_PREFIX)
app.include_router(kb_router,       prefix=API_PREFIX)
app.include_router(prompt_router,   prefix=API_PREFIX)
app.include_router(examples_router, prefix=API_PREFIX)
app.include_router(sections_router, prefix=API_PREFIX)

# Healthchecks (one unprefixed, optionally one prefixed in prod)
@app.get("/healthz")
def healthz():
    return {"status": "ok", "env": APP_ENV, "prefix": API_PREFIX or "/"}

if API_PREFIX:
    @app.get(f"{API_PREFIX}/healthz")
    def healthz_api():
        return {"status": "ok", "env": APP_ENV, "prefix": API_PREFIX}

@app.on_event("startup")
async def startup_event():
    db: Session = None
    try:
        db = get_db().__next__()
        _seed_prompt_functions_logic(db=db)
    finally:
        if db:
            db.close()
