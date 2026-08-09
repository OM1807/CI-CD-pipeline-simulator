from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uuid

from . import models, schemas
from .queue import job_queue
from .models import SessionLocal
from .websocket import ws_router

app = FastAPI(title="CI/CD Pipeline Simulator")

app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def prepare_build_response(build: models.Build) -> dict:
    resp = build.__dict__.copy()
    if build.started_at and build.finished_at:
        resp["duration_seconds"] = int((build.finished_at - build.started_at).total_seconds())
    else:
        resp["duration_seconds"] = None
    return resp

@app.post("/builds", response_model=schemas.BuildResponse, status_code=201)
def create_build(build_req: schemas.BuildCreate, db: Session = Depends(get_db)):
    build_id = f"b_{uuid.uuid4().hex[:8]}"
    
    new_build = models.Build(
        id=build_id,
        repo_url=build_req.repo_url,
        branch=build_req.branch,
        steps=build_req.steps,
        image=build_req.image,
    )
    db.add(new_build)
    db.commit()
    db.refresh(new_build)
    
    # Enqueue job
    job_queue.enqueue("app.worker.run_build", build_id)
    
    return prepare_build_response(new_build)

@app.get("/builds", response_model=List[schemas.BuildResponse])
def get_builds(db: Session = Depends(get_db)):
    builds = db.query(models.Build).order_by(models.Build.created_at.desc()).all()
    return [prepare_build_response(b) for b in builds]

@app.get("/builds/{build_id}", response_model=schemas.BuildResponse)
def get_build(build_id: str, db: Session = Depends(get_db)):
    build = db.query(models.Build).filter(models.Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    return prepare_build_response(build)
