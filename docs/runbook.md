# Runbook

## Local Development
1. Copy `infra/env.example` to `.env` and adjust secrets.
2. From `infra/`, run `docker-compose up --build` to start API, Postgres, Redis, and worker.
3. Run migrations: `docker-compose exec api alembic upgrade head`.
4. Access API at `http://localhost:8000`.

## Background Jobs
- `jobs.ingest_source(source_name)` to pull raw listings from connectors.
- `jobs.normalize_raw_listing(raw_id)` to transform and store normalized listings.
- `jobs.recompute_market_stats(region_key, model_key)` to refresh medians/quartiles.
- `jobs.daily_opportunities(region_key)` to scan for curated picks.

### Scheduling (cron examples)
- Ingestion: `0 * * * *` hourly per source.
- Normalization: `*/10 * * * *` for newly ingested rows.
- Market stats: `0 3 * * *` daily.
- Opportunities: `15 3 * * *` daily after stats.

## Scraping Safety
- Connectors must respect robots.txt and marketplace ToS.
- Use Playwright with rate limiting and user-agent rotation as needed.
- Do **not** hardcode credentials or bypass protections.

## Troubleshooting
- Check container logs (`docker-compose logs api`).
- Ensure `DATABASE_URL` and `REDIS_URL` are reachable from containers.
