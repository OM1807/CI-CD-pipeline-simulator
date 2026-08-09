# CI/CD Pipeline Simulator

A lightweight, self-hosted CI/CD system that clones a Git repository, runs its test suite inside an isolated Docker container, and reports build status through a web dashboard — with parallel job execution, automatic retries, and live log streaming.

Think of it as a miniature Jenkins / GitHub Actions, built from scratch to understand how real CI/CD systems work internally.

---

## 1. Problem Statement

Modern CI/CD systems (Jenkins, GitHub Actions, CircleCI) do three core things:
1. Take a code change and run it in an isolated environment
2. Execute a defined set of build/test steps
3. Report results and keep a history, so failures are caught before deployment

This project rebuilds that core loop in a simplified, self-contained way, focusing on **job queuing, container isolation, concurrency, retries, and observability**.

---

## 2. Tech Stack (100% free / open-source)

| Layer | Tool | Notes |
|---|---|---|
| API server | **FastAPI** (Python) | Exposes REST endpoints to submit and query builds |
| Job queue | **Redis + RQ** | Redis runs locally via Docker; RQ is a simple Python job queue built on Redis |
| Worker execution | **Docker Engine** (Docker SDK for Python) | Each build job runs inside its own throwaway container |
| Database | **PostgreSQL** | Stores build metadata, logs, and history |
| Real-time updates | **WebSockets** (via FastAPI) | Streams live logs to the dashboard while a build runs |
| Frontend | **React** (Vite) + plain CSS or Tailwind | Dashboard UI |
| Containerization / local run | **Docker Compose** | Spins up API, worker(s), Redis, Postgres, and frontend together |

No paid services, no cloud API keys required. Everything runs with `docker-compose up`.

---

## 3. High-Level Architecture

```
                ┌─────────────┐
   User/Browser │  React UI   │
                └──────┬──────┘
                       │ REST + WebSocket
                       ▼
                ┌─────────────┐
                │  FastAPI    │◄──────────────┐
                │  API Server │                │
                └──────┬──────┘                │
                       │ enqueue job            │ status/log updates
                       ▼                        │
                ┌─────────────┐          ┌───────┴──────┐
                │ Redis Queue │─────────▶│ RQ Worker(s) │
                │   (RQ)      │          │ (N processes)│
                └─────────────┘          └──────┬───────┘
                                                 │ spins up
                                                 ▼
                                          ┌─────────────┐
                                          │ Docker      │
                                          │ Container   │
                                          │ (per build) │
                                          └──────┬───────┘
                                                 │ writes result
                                                 ▼
                                          ┌─────────────┐
                                          │ PostgreSQL  │
                                          │ (build data)│
                                          └─────────────┘
```

---

## 4. Core Features (MVP — build this first)

- [ ] **Submit a build job**: `POST /builds` accepts a Git repo URL + a `pipeline.yaml` (or inline list of shell commands)
- [ ] **Queue the job** in Redis via RQ
- [ ] **Worker picks up the job**, clones the repo, and runs it inside a fresh Docker container (e.g. `python:3.11-slim` or `node:20-slim` depending on project type)
- [ ] **Capture logs and exit code** from the container run
- [ ] **Persist build record** in PostgreSQL: id, repo URL, status (`queued` / `running` / `passed` / `failed`), start time, end time, logs
- [ ] **List builds**: `GET /builds` returns build history
- [ ] **Get build detail**: `GET /builds/{id}` returns full logs and status for one build
- [ ] **Dashboard UI**: table of past builds with color-coded status badges; click a row to view full logs

## 5. Stretch Features (build after MVP works end-to-end)

- [ ] **Parallel workers**: run multiple RQ workers concurrently so multiple builds execute at the same time
- [ ] **Retry logic**: automatically re-queue a failed build up to N times before marking it permanently failed
- [ ] **Live log streaming**: instead of only showing logs after completion, stream stdout/stderr line-by-line over WebSocket while the container runs
- [ ] **Monitoring dashboard**: small charts/metrics — current queue depth, average build duration, success rate over last N builds
- [ ] **GitHub webhook trigger**: `POST /webhook/github` endpoint that auto-starts a build when a push event is received
- [ ] **Build cancellation**: allow cancelling a queued or running build

---

## 6. API Specification

### `POST /builds`
Submit a new build job.

**Request body:**
```json
{
  "repo_url": "https://github.com/user/example-repo",
  "branch": "main",
  "steps": [
    "pip install -r requirements.txt",
    "pytest"
  ],
  "image": "python:3.11-slim"
}
```

**Response (201):**
```json
{
  "id": "b_123abc",
  "status": "queued",
  "created_at": "2026-07-30T10:00:00Z"
}
```

### `GET /builds`
Returns a list of builds, most recent first.

**Response (200):**
```json
[
  {
    "id": "b_123abc",
    "repo_url": "https://github.com/user/example-repo",
    "status": "passed",
    "created_at": "2026-07-30T10:00:00Z",
    "finished_at": "2026-07-30T10:01:42Z",
    "duration_seconds": 102
  }
]
```

### `GET /builds/{id}`
Returns full detail for a single build, including logs.

**Response (200):**
```json
{
  "id": "b_123abc",
  "repo_url": "https://github.com/user/example-repo",
  "branch": "main",
  "status": "passed",
  "steps": ["pip install -r requirements.txt", "pytest"],
  "logs": "Cloning repo...\nInstalling dependencies...\n... test output ...\n5 passed in 2.1s",
  "exit_code": 0,
  "created_at": "2026-07-30T10:00:00Z",
  "started_at": "2026-07-30T10:00:05Z",
  "finished_at": "2026-07-30T10:01:42Z",
  "retry_count": 0
}
```

### `WS /builds/{id}/logs`
WebSocket endpoint. Streams log lines as they're produced during a running build. Closes when the build finishes.

### `POST /webhook/github` (stretch)
Receives a GitHub push webhook payload and automatically creates a build job for the pushed branch.

---

## 7. Database Schema (PostgreSQL)

```sql
CREATE TABLE builds (
    id VARCHAR PRIMARY KEY,
    repo_url TEXT NOT NULL,
    branch VARCHAR DEFAULT 'main',
    steps JSONB NOT NULL,
    image VARCHAR DEFAULT 'python:3.11-slim',
    status VARCHAR NOT NULL DEFAULT 'queued', -- queued | running | passed | failed
    logs TEXT DEFAULT '',
    exit_code INTEGER,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT now(),
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);
```

---

## 8. Worker Logic (pseudocode)

```
def run_build(build_id):
    build = fetch_build(build_id)
    update_status(build_id, "running", started_at=now())

    container = docker_client.containers.run(
        image=build.image,
        command="sh -c 'git clone {repo_url} . && {steps_joined_by_&&}'",
        detach=True,
        working_dir="/app"
    )

    for line in container.logs(stream=True):
        append_log(build_id, line)
        broadcast_to_websocket(build_id, line)   # stretch feature

    exit_code = container.wait()["StatusCode"]
    container.remove()

    if exit_code == 0:
        update_status(build_id, "passed", finished_at=now())
    else:
        if build.retry_count < MAX_RETRIES:
            increment_retry(build_id)
            enqueue_again(build_id)              # stretch feature
        else:
            update_status(build_id, "failed", finished_at=now())
```

---

## 9. Folder Structure

```
ci-cd-simulator/
├── docker-compose.yml
├── README.md
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, routes
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── worker.py          # RQ job function (run_build)
│   │   ├── queue.py           # Redis/RQ connection setup
│   │   ├── docker_runner.py   # Docker SDK logic to run a build container
│   │   └── websocket.py       # Live log streaming
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── BuildList.jsx
│   │   │   ├── BuildDetail.jsx
│   │   │   └── StatusBadge.jsx
│   │   └── api.js
│   ├── package.json
│   └── Dockerfile
└── .env.example
```

---

## 10. Environment Variables (`.env`)

```
DATABASE_URL=postgresql://ciuser:cipass@postgres:5432/cicd_db
REDIS_URL=redis://redis:6379/0
MAX_RETRIES=2
DEFAULT_DOCKER_IMAGE=python:3.11-slim
```

---

## 11. Running Locally

```bash
git clone <this-repo>
cd ci-cd-simulator
docker-compose up --build
```

This should start:
- `postgres` — database on port 5432
- `redis` — queue on port 6379
- `backend` — FastAPI on port 8000
- `worker` — RQ worker process consuming jobs
- `frontend` — React dashboard on port 5173

Then submit a test build:
```bash
curl -X POST http://localhost:8000/builds \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pallets/flask-example",
    "steps": ["pip install -r requirements.txt", "pytest"]
  }'
```

---

## 12. Build Order (recommended implementation sequence)

1. Set up `docker-compose.yml` with Postgres + Redis running
2. Build FastAPI skeleton with `POST /builds` and `GET /builds` (no queue yet — just save to DB)
3. Add Redis + RQ; move build execution into a queued worker job
4. Add `docker_runner.py`: clone repo + run steps inside a container using the Docker SDK
5. Add `GET /builds/{id}` with full logs
6. Build the React dashboard: list view + detail view
7. Add WebSocket log streaming
8. Add retry logic
9. Add multiple concurrent workers (`docker-compose up --scale worker=3`)
10. Add basic monitoring dashboard (queue depth, success rate)
11. (Optional) Add GitHub webhook trigger

---

## 13. Notes / Constraints

- Each build **must** run in its own container to guarantee isolation between jobs.
- The Docker socket (`/var/run/docker.sock`) needs to be mounted into the worker container so it can launch sibling containers ("Docker-in-Docker via socket mounting").
- Keep the whole stack running on `docker-compose` only — no paid cloud services are required for any part of this project.
