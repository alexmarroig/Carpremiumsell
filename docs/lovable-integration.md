# Lovable Integration Guide

This guide summarizes the endpoints and payloads needed to integrate AXIS in Lovable.

## Base URLs
- **Local:** `http://localhost:8000`
- **Swagger UI:** `/docs`
- **OpenAPI schema:** `/openapi.json`

## Required Endpoints

### Health
`GET /health`
- Use for startup checks.

### Auth (optional)
`POST /v1/auth/register`
- Body: `{ "email": "demo@example.com", "password": "pass" }`

`POST /v1/auth/login`
- Body: `{ "email": "demo@example.com", "password": "pass" }`
- Response: `{ "access_token": "<jwt>", "token_type": "bearer" }`

### Search + Axis Bot
`POST /v1/search`
- Body: `{ "query": "SUV até 150k em SP", "preferences": { ... } }`
- Response: `{ "session_id": "<uuid>" }`

`POST /v1/axis-bot/chat`
- Body: `{ "session_id": "<uuid>", "message": "Quero um SUV premium até 180k" }`
- Response: `{ "reply": "...", "listing": { ... } }`

### Listings
`GET /v1/opportunities?region=SP`
- Response: `{ "items": [ListingOut], "count": 1 }`

`GET /v1/listings/{listing_id}`
- Response: `ListingOut`

`GET /v1/trusted-sellers?limit=10&origin=mercadolivre`
- Response: `[SellerStatsOut]`

### Selling
`POST /v1/sell/estimate`
- Body: `{ "description": "BMW X1 2022", "mileage_km": 22000, "region": "SP" }`
- Response: `{ "min_price": 76000, "max_price": 84000, "rationale": "..." }`

## Notes for Lovable
- All responses are JSON.
- CORS is enabled via `CORS_ORIGINS` (defaults to `*`).
- Rate limit defaults to 60 requests/min per IP (`RATE_LIMIT_PER_MINUTE`).
- Use `/openapi.json` for client generation.
