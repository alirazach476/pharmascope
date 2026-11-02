# Deployment

## Local (recommended first)

1. Create venv and `pip install -e ".[dev]"`  
2. Copy `.env.example` to `.env`  
3. Run bounded ingestion + transforms  
4. Start API and dashboard processes  

## Docker Compose

```bash
docker compose up --build
```

- API: http://localhost:8000/health  
- Dashboard: http://localhost:8501  

Volumes mount `./data` and `./reports` for persistence.

**Resource note:** Lightweight laptop profile uses bounded samples (≤1000 records).
Do not enable full downloads inside Compose without disk/rate-limit planning.

## Cloud

No cloud provider is configured in this repository. Do not claim cloud deployment
until services are actually provisioned and documented.
