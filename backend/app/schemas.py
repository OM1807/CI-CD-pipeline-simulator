from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BuildCreate(BaseModel):
    repo_url: str
    branch: Optional[str] = "main"
    steps: List[str]
    image: Optional[str] = "python:3.11-slim"

class BuildResponse(BaseModel):
    id: str
    repo_url: str
    branch: str
    steps: List[str]
    image: str
    status: str
    logs: str
    exit_code: Optional[int] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None

    class Config:
        from_attributes = True
