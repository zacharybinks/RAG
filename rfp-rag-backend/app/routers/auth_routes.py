# Auto-generated during refactor (complete blocks)
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os, shutil, tempfile, traceback, re
import crud, models, schemas, auth
from app.deps import get_db
from app.core.config import PROJECTS_DIRECTORY, DB_DIRECTORY, KNOWLEDGE_BASE_DIRECTORY, APP_ENV
from app.services.document_service import process_document, sanitize_name_for_directory, num_tokens_from_string

router = APIRouter()

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Restrict registration by email domain
    domain = user.username.split("@")[-1] if "@" in user.username else ""
    allowed_domains = ["avatar-computing.com", "sossecinc.com"]
    if domain.lower() not in allowed_domains:
        raise HTTPException(status_code=400, detail="Registration is restricted.")

    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@router.get("/users/me/", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(auth.get_current_active_user),
):
    return current_user
