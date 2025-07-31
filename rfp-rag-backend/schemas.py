# -------------------------------------------------------------------
# File: rfp-rag-backend/schemas.py (Complete & Corrected)
# Description: Pydantic models for data validation and shaping.
# -------------------------------------------------------------------
from pydantic import BaseModel, Field
from typing import List, Tuple, Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
class UserCreate(UserBase):
    password: str
class User(UserBase):
    id: int
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
class TokenData(BaseModel):
    username: Optional[str] = None

class ChatMessageBase(BaseModel):
    message_type: str
    text: str
class ChatMessageCreate(ChatMessageBase):
    pass
class ChatMessage(ChatMessageBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class RfpProjectBase(BaseModel):
    name: str
class RfpProjectCreate(RfpProjectBase):
    project_id: str
class RfpProjectUpdate(RfpProjectBase):
    pass
class RfpProject(RfpProjectBase):
    id: int
    project_id: str
    system_prompt: str
    owner_id: int
    chat_messages: List[ChatMessage] = []
    class Config:
        from_attributes = True

class PromptFunctionBase(BaseModel):
    module_name: str
    function_name: str
    button_label: str
    prompt_text: str
    description: Optional[str] = None
class PromptFunctionCreate(PromptFunctionBase):
    pass
class PromptFunctionUpdate(PromptFunctionBase):
    pass
class PromptFunction(PromptFunctionBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

class QueryRequest(BaseModel):
    query: Optional[str] = None
    prompt_function_id: Optional[int] = None

class Settings(BaseModel):
    system_prompt: str