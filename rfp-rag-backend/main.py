# Refactored FastAPI application entrypoint
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import origins
from app.deps import get_db
from sqlalchemy.orm import Session
import crud
from app.services.prompt_service import _seed_prompt_functions_logic

app = FastAPI(title="RFP RAG Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
from app.routers.auth_routes import router as auth_router
from app.routers.rfp_routes import router as rfp_router
from app.routers.kb_routes import router as kb_router
from app.routers.prompt_functions_routes import router as prompt_router

app.include_router(auth_router)
app.include_router(rfp_router)
app.include_router(kb_router)
app.include_router(prompt_router)

@app.on_event("startup")
async def startup_event():
    db: Session = None
    try:
        db = get_db().__next__()
        _seed_prompt_functions_logic(db=db)
    finally:
        if db:
            db.close()

