# rfp-rag-backend/crud.py

from sqlalchemy.orm import Session
import models, schemas, auth
from typing import List, Tuple

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()
def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_project_by_project_id(db: Session, project_id: str):
    return db.query(models.RfpProject).filter(models.RfpProject.project_id == project_id).first()
def get_projects_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.RfpProject).filter(models.RfpProject.owner_id == user_id).order_by(models.RfpProject.id.desc()).offset(skip).limit(limit).all()

def create_rfp_project(db: Session, project: schemas.RfpProjectCreate, user_id: int):
    db_project = models.RfpProject(
        name=project.name, 
        project_id=project.project_id, 
        owner_id=user_id, 
        system_prompt=f"You are a proposal writer... The current project is '{project.name}'.",
        model_name="gpt-3.5-turbo",
        temperature=0.2,
        #context_amount=15,  # We'll retrieve more documents to re-rank
        context_size='medium'
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, project_id: str, project_update: schemas.RfpProjectUpdate, user_id: int):
    db_project = db.query(models.RfpProject).filter(models.RfpProject.project_id == project_id, models.RfpProject.owner_id == user_id).first()
    if db_project:
        db_project.name = project_update.name
        db.commit()
        db.refresh(db_project)
    return db_project
def delete_project(db: Session, project_id: str, user_id: int):
    db_project = db.query(models.RfpProject).filter(models.RfpProject.project_id == project_id, models.RfpProject.owner_id == user_id).first()
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False

def update_settings(db: Session, project_id: str, settings: schemas.Settings, user_id: int):
    db_project = db.query(models.RfpProject).filter(models.RfpProject.project_id == project_id, models.RfpProject.owner_id == user_id).first()
    if db_project:
        db_project.system_prompt = settings.system_prompt
        db_project.model_name = settings.model_name
        db_project.temperature = settings.temperature
        # db_project.context_amount = settings.context_amount # <-- This line is removed
        db_project.context_size = settings.context_size
        db.commit()
        db.refresh(db_project)
    return db_project

def create_chat_message(db: Session, message: schemas.ChatMessageCreate, project_id: int):
    db_message = models.ChatMessage(**message.dict(), project_id=project_id)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def delete_chat_history(db: Session, project_id: int):
    """Deletes all chat messages for a given project."""
    num_deleted = db.query(models.ChatMessage).filter(models.ChatMessage.project_id == project_id).delete(synchronize_session=False)
    db.commit()
    return num_deleted

def get_chat_history_for_model(db: Session, project_id: int) -> List[Tuple[str, str]]:
    history = db.query(models.ChatMessage).filter(models.ChatMessage.project_id == project_id).order_by(models.ChatMessage.created_at).all()
    chat_history_tuples = []
    for i in range(0, len(history), 2):
        if i + 1 < len(history) and history[i].message_type == 'query' and history[i+1].message_type == 'answer':
            chat_history_tuples.append((history[i].text, history[i+1].text))
    return chat_history_tuples

def get_prompt_function(db: Session, function_id: int):
    return db.query(models.PromptFunction).filter(models.PromptFunction.id == function_id).first()
def get_prompt_function_by_name(db: Session, function_name: str):
    return db.query(models.PromptFunction).filter(models.PromptFunction.function_name == function_name).first()
def get_prompt_functions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.PromptFunction).filter(models.PromptFunction.is_active == True).order_by(models.PromptFunction.module_name, models.PromptFunction.id).offset(skip).limit(limit).all()
def create_prompt_function(db: Session, function: schemas.PromptFunctionCreate):
    db_function = models.PromptFunction(**function.dict())
    db.add(db_function)
    db.commit()
    db.refresh(db_function)
    return db_function
def update_prompt_function(db: Session, function_id: int, function_update: schemas.PromptFunctionUpdate):
    db_function = db.query(models.PromptFunction).filter(models.PromptFunction.id == function_id).first()
    if db_function:
        update_data = function_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_function, key, value)
        db.commit()
        db.refresh(db_function)
    return db_function

def get_knowledge_base_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.KnowledgeBaseDocument).offset(skip).limit(limit).all()

def create_knowledge_base_document(db: Session, document: schemas.KnowledgeBaseDocumentCreate):
    db_document = models.KnowledgeBaseDocument(**document.dict())
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def delete_knowledge_base_document(db: Session, document_name: str):
    db_document = db.query(models.KnowledgeBaseDocument).filter(models.KnowledgeBaseDocument.document_name == document_name).first()
    if db_document:
        db.delete(db_document)
        db.commit()
        return True
    return False
