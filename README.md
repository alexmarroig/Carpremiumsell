# AXIS Premium Car Backend

API-first backend for AXIS, a premium car-curation product for Brazil.

## Getting Started
1. Install Docker and docker-compose.
2. Copy `infra/env.example` to `.env`.
3. From `infra/`, run:
   ```bash
   docker-compose up --build
   docker-compose exec api alembic upgrade head
   ```
4. API available at `http://localhost:8000`.

## Sample Requests
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/auth/register -H "Content-Type: application/json" -d '{"email":"demo@example.com","password":"pass"}'
curl -X POST http://localhost:8000/v1/search -H "Content-Type: application/json" -d '{"query":"SUV até 150k em SP"}'
```

## Components
- **FastAPI** app with JWT auth and rate limiting.
- **PostgreSQL** + **Alembic** migrations for models (users, listings, stats, alerts, recommendations).
- **Redis + RQ** workers for ingestion and analytics.
- **Connectors** framework with safe example stub.
- **Axis Bot** service orchestrating AI provider and selecting a single recommendation.

See `docs/architecture.md`, `docs/api.md`, and `docs/runbook.md` for details.
