from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") 
if not SQLALCHEMY_DATABASE_URL:
    raise EnvironmentError("DATABASE_URL must be set in the environment.")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()