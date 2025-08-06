# rfp-rag-backend/schemas.py

from pydantic import BaseModel, Field, EmailStr
from typing import List, Tuple, Optional, Literal
from datetime import datetime

class UserBase(BaseModel):
    username: EmailStr
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
    model_name: str
    temperature: float
    # context_amount: int # <-- This line is removed
    context_size: str
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
    use_knowledge_base: bool = False

class Settings(BaseModel):
    system_prompt: str
    model_name: str
    temperature: float
    # context_amount: int
    context_size: Literal['low', 'medium', 'high'] = 'medium'

class KnowledgeBaseDocumentBase(BaseModel):
    document_name: str
    description: Optional[str] = None

class KnowledgeBaseDocumentCreate(KnowledgeBaseDocumentBase):
    pass

class KnowledgeBaseDocument(KnowledgeBaseDocumentBase):
    id: int
    class Config:
        from_attributes = True