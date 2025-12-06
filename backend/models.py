from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel

class ChatMessage(Base):
    """SQLAlchemy model for storing chat history."""
    
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_query = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")
    
    
class User(Base):
    __tablename__ = "users"  
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    hashed_password = Column(String, nullable=False)
    
  