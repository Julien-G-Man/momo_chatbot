from sqlalchemy.orm import Session
from database import SessionLocal

def get_db():
    """Provides a fresh database session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()