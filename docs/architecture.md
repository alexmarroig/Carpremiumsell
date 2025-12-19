# AXIS Backend Architecture

## Overview
- **Framework**: FastAPI for REST APIs used by web and mobile clients.
- **Database**: PostgreSQL with SQLAlchemy 2.0 ORM and Alembic migrations.
- **Cache/Queue**: Redis with RQ for ingestion and analytics jobs.
- **Scraping**: Playwright-driven connectors (stub provided) respecting robots.txt/ToS.
- **AI Orchestration**: Provider interface with mock implementation powering Axis Bot.

## Modules
- `app/api`: HTTP routers including auth, search, listings, Axis Bot, health.
- `app/services`: Pricing, trust filtering, normalization, recommendations, AI providers.
- `app/connectors`: Base connector pattern and example marketplace stub.
- `app/workers`: RQ jobs for ingestion, normalization, market stats, opportunities.
- `app/models`: SQLAlchemy models for all domain entities.

## Data Flow
1. **Ingestion** loads raw listings into `raw_listings` via connector fetchers.
2. **Normalization** maps raw payloads into structured `normalized_listings`, applies markup and trust logic.
3. **Market stats** recompute medians and quartiles per region/model for opportunity detection.
4. **Axis Bot** sessions capture natural-language intents, then select a single listing and respond in Portuguese.
5. **APIs** expose curated listings, details, search sessions, auth, and selling estimates.

## Observability & Security
- Structured logging to stdout.
- Basic Redis rate limiter middleware.
- CORS configurable via environment.
- JWT-based auth for protected endpoints.
