# Runbook

## Local Development
1. Copy `infra/env.example` to `.env` and adjust secrets.
2. From `infra/`, run `docker-compose up --build` to start API, Postgres, Redis, and worker.
3. Run migrations: `docker-compose exec api alembic upgrade head`.
4. Access API at `http://localhost:8000`.

## Background Jobs
- `jobs.ingest_source(source_name)` to pull raw listings from connectors.
- `jobs.ingest_marketplace(source="mercadolivre", region_key="sp-sao-paulo", query_text="corolla 2020")` to ingest public Mercado Livre listings (cars and others) with rate limits.
- `jobs.normalize_raw_listing(raw_id)` to transform and store normalized listings.
- `jobs.recompute_market_stats(region_key, model_key)` to refresh medians/quartiles.
- `jobs.daily_opportunities(region_key)` to scan for curated picks.

To run ingestion locally via the internal API, POST to `/internal/ingest/mercadolivre` with a JSON body such as `{ "region_key": "sp-sao-paulo", "query_text": "corolla 2020 automatico", "limit": 30 }`.

### Ingestion rate limits
- Configure via env: `MERCADOLIVRE_RATE_LIMIT_PER_MINUTE`, `MERCADOLIVRE_MIN_DELAY_SECONDS`, `MERCADOLIVRE_MAX_DELAY_SECONDS`, and `MERCADOLIVRE_HEADLESS`.
- Strong backoff and randomized delays are applied per page fetch; defaults keep requests low-volume and polite.

### Scheduling (cron examples)
- Ingestion: `0 * * * *` hourly per source.
- Normalization: `*/10 * * * *` for newly ingested rows.
- Market stats: `0 3 * * *` daily.
- Opportunities: `15 3 * * *` daily after stats.

## Scraping Safety
- Connectors must respect robots.txt and marketplace ToS.
- Use Playwright with rate limiting and user-agent rotation as needed.
- Do **not** hardcode credentials or bypass protections.
- Mercado Livre connector fetches only public listing pages (no login), blocks heavy resources, and excludes personal data (no seller names/phones/emails/user IDs). Ensure new connectors follow the same posture.

## Troubleshooting
- Check container logs (`docker-compose logs api`).
- Ensure `DATABASE_URL` and `REDIS_URL` are reachable from containers.
