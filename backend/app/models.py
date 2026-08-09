from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ciuser:cipass@postgres:5432/cicd_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_utc_now():
    return datetime.now(timezone.utc)

class Build(Base):
    __tablename__ = "builds"

    id = Column(String, primary_key=True, index=True)
    repo_url = Column(Text, nullable=False)
    branch = Column(String, default="main")
    steps = Column(JSON, nullable=False)
    image = Column(String, default="python:3.11-slim")
    status = Column(String, default="queued", nullable=False)
    logs = Column(Text, default="")
    exit_code = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)
