import os
from sqlalchemy.orm import Session
from .models import SessionLocal, Build, get_utc_now
from .docker_runner import run_in_docker
from .queue import redis_conn

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

def append_log(db: Session, build_id: str, line: str):
    build = db.query(Build).filter(Build.id == build_id).first()
    if build:
        build.logs += line
        db.commit()
    # Publish to Redis for WebSocket clients
    redis_conn.publish(f"build-logs:{build_id}", line)

def run_build(build_id: str):
    db = SessionLocal()
    try:
        build = db.query(Build).filter(Build.id == build_id).first()
        if not build:
            return

        build.status = "running"
        build.started_at = get_utc_now()
        db.commit()
        
        def log_cb(line):
            append_log(db, build_id, line)
            
        exit_code = run_in_docker(build.image, build.repo_url, build.steps, log_cb)
        
        build = db.query(Build).filter(Build.id == build_id).first()
        build.exit_code = exit_code
        
        if exit_code == 0:
            build.status = "passed"
            build.finished_at = get_utc_now()
        else:
            if build.retry_count < MAX_RETRIES:
                build.retry_count += 1
                build.status = "queued"
                build.logs += f"\n--- Build failed with exit code {exit_code}. Retrying ({build.retry_count}/{MAX_RETRIES}) ---\n"
                db.commit()
                # Re-queue job
                from .queue import job_queue
                job_queue.enqueue("app.worker.run_build", build_id)
                return
            else:
                build.status = "failed"
                build.finished_at = get_utc_now()
                
        db.commit()
        redis_conn.publish(f"build-logs:{build_id}", "__EOF__")
        
    except Exception as e:
        build = db.query(Build).filter(Build.id == build_id).first()
        if build:
            build.status = "failed"
            build.logs += f"\nInternal Error: {str(e)}\n"
            build.finished_at = get_utc_now()
            db.commit()
            redis_conn.publish(f"build-logs:{build_id}", "__EOF__")
    finally:
        db.close()
