from pydantic import BaseModel
from typing import Optional

# --- Authentication Schemas ---

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str 
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class ChatRequest(BaseModel):
    """Schema for the incoming chat request from the frontend."""
    message: str

class ChatResponse(BaseModel):
    """Schema for the outgoing chat response to the frontend."""
    response: str
    source: Optional[str] = None    