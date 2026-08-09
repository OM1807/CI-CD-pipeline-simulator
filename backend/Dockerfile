FROM python:3.11-slim

# Install git, docker CLI for running jobs inside containers
RUN apt-get update && apt-get install -y git docker.io curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run uvicorn by default (worker will override this)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
