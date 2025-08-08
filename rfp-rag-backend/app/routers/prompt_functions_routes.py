# Auto-generated during refactor (complete blocks)
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os, shutil, tempfile, traceback, re
import crud, models, schemas, auth
from app.deps import get_db
from app.core.config import PROJECTS_DIRECTORY, DB_DIRECTORY, KNOWLEDGE_BASE_DIRECTORY, APP_ENV
from app.services.document_service import process_document, sanitize_name_for_directory, num_tokens_from_string
from app.services.prompt_service import get_prompt_functions, create_prompt_function, update_prompt_function, _seed_prompt_functions_logic
router = APIRouter()

@router.get("/prompt-functions/", response_model=List[schemas.PromptFunction])
def get_prompt_functions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    return crud.get_prompt_functions(db=db)


@router.post("/prompt-functions/", response_model=schemas.PromptFunction, status_code=201)
def create_prompt_function(function_data: schemas.PromptFunctionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    existing = crud.get_prompt_function_by_name(db, function_name=function_data.function_name)
    if existing:
        raise HTTPException(status_code=400, detail="A function with this name already exists.")
    return crud.create_prompt_function(db, function=function_data)


@router.put("/prompt-functions/{function_id}", response_model=schemas.PromptFunction)
def update_prompt_function(function_id: int, function_update: schemas.PromptFunctionUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_active_user)):
    db_function = crud.update_prompt_function(db, function_id, function_update)
    if not db_function:
        raise HTTPException(status_code=404, detail="Prompt function not found")
    return db_function


@router.post("/seed-prompt-functions/", status_code=201)
def seed_prompt_functions_endpoint(db: Session = Depends(get_db)):
    _seed_prompt_functions_logic(db=db)
    return {"message": "Seeding of prompt functions complete."}
