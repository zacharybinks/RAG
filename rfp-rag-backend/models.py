# -------------------------------------------------------------------
# File: rfp-rag-backend/models.py (Complete & Corrected)
# Description: Defines the database tables as Python classes.
# -------------------------------------------------------------------
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    projects = relationship("RfpProject", back_populates="owner", cascade="all, delete-orphan")

class RfpProject(Base):
    __tablename__ = "rfp_projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_id = Column(String, unique=True, index=True)
    system_prompt = Column(Text, default="You are a helpful assistant.")
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="projects")
    chat_messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("rfp_projects.id"))
    message_type = Column(String)
    text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    project = relationship("RfpProject", back_populates="chat_messages")

class PromptFunction(Base):
    __tablename__ = "prompt_functions"
    id = Column(Integer, primary_key=True, index=True)
    module_name = Column(String, index=True)
    function_name = Column(String, unique=True)
    button_label = Column(String)
    prompt_text = Column(Text)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)