# API Surface

## Overview
- **Base URL (local):** `http://localhost:8000`
- **Content-Type:** `application/json`
- **OpenAPI docs:** `/docs` (Swagger UI), `/openapi.json` (schema)
- **Auth:** JWT bearer tokens via `Authorization: Bearer <token>` when needed. (Current endpoints are public unless protected in the future.)
- **Rate limit:** Defaults to **60 requests/min** per client IP (configurable via `RATE_LIMIT_PER_MINUTE`).

### Error Responses
FastAPI returns JSON errors in the shape:
```json
{ "detail": "message" }
```
Common status codes:
- `400` invalid input (e.g., duplicate email)
- `401` invalid credentials
- `422` validation error
- `429` too many requests

---

## Health
### `GET /health`
**Response**
```json
{ "status": "ok" }
```

---

## Auth
### `POST /v1/auth/register`
Create a user.

**Request**
```json
{ "email": "demo@example.com", "password": "pass" }
```

**Response**
```json
{ "id": 1, "email": "demo@example.com", "created_at": "2024-05-10T12:00:00Z" }
```

### `POST /v1/auth/login`
Authenticate and receive a JWT access token.

**Request**
```json
{ "email": "demo@example.com", "password": "pass" }
```

**Response**
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

---

## Listings
### `GET /v1/opportunities?region=SP`
Return a curated list of listings with opportunity and/or trust badges.

**Query Params**
- `region` (required): region key (e.g., `SP`).

**Response**
```json
{
  "items": [
    {
      "id": 123,
      "brand": "BMW",
      "model": "X1",
      "trim": "xDrive",
      "year": 2022,
      "mileage_km": 22000,
      "price_brl": 190000,
      "final_price_brl": 185000,
      "city": "São Paulo",
      "state": "SP",
      "photos": ["https://..."],
      "url": "https://...",
      "seller_type": "dealer",
      "seller_id": 55,
      "badge": "Selected by AXIS",
      "status": "active",
      "created_at": "2024-05-10T12:00:00Z",
      "updated_at": "2024-05-12T09:00:00Z"
    }
  ],
  "count": 1
}
```

### `GET /v1/trusted-sellers?limit=10&origin=mercadolivre`
Return aggregated seller trust metrics.

**Query Params**
- `limit` (optional, 1-50): max sellers to return (default 10).
- `origin` (optional): marketplace origin filter.

**Response**
```json
[
  {
    "seller_id": 55,
    "origin": "mercadolivre",
    "reputation_medal": "gold",
    "reputation_score": 4.9,
    "cancellations": 2,
    "response_time_hours": 2.5,
    "completed_sales": 180,
    "average_price_brl": 175000,
    "listings_count": 12,
    "problem_rate": 0.02,
    "reliability_score": 0.98
  }
]
```

### `GET /v1/listings/{listing_id}`
Return a single listing by ID.

**Response**
```json
{
  "id": 123,
  "brand": "BMW",
  "model": "X1",
  "trim": "xDrive",
  "year": 2022,
  "mileage_km": 22000,
  "price_brl": 190000,
  "final_price_brl": 185000,
  "city": "São Paulo",
  "state": "SP",
  "photos": ["https://..."],
  "url": "https://...",
  "seller_type": "dealer",
  "seller_id": 55,
  "badge": "Verified listing",
  "status": "active",
  "created_at": "2024-05-10T12:00:00Z",
  "updated_at": "2024-05-12T09:00:00Z"
}
```

---

## Search & Axis Bot
### `POST /v1/search`
Start a search session for conversational guidance.

**Request**
```json
{ "query": "SUV até 150k em SP", "preferences": { "brand": "Audi" } }
```

**Response**
```json
{ "session_id": "<uuid>" }
```

### `POST /v1/axis-bot/chat`
Send a chat message to Axis Bot and receive a reply + optional single listing recommendation.

**Request**
```json
{ "session_id": "<uuid>", "message": "Quero um SUV premium até 180k" }
```

**Response**
```json
{
  "reply": "Encontrei uma opção com ótimo custo-benefício...",
  "listing": {
    "id": 123,
    "brand": "BMW",
    "model": "X1",
    "trim": "xDrive",
    "year": 2022,
    "mileage_km": 22000,
    "price_brl": 190000,
    "final_price_brl": 185000,
    "city": "São Paulo",
    "state": "SP",
    "photos": ["https://..."],
    "url": "https://...",
    "seller_type": "dealer",
    "seller_id": 55,
    "badge": "Selected by AXIS",
    "status": "active",
    "created_at": "2024-05-10T12:00:00Z",
    "updated_at": "2024-05-12T09:00:00Z"
  }
}
```

---

## Sell Estimate
### `POST /v1/sell/estimate`
Return a price range estimate for a car a user wants to sell.

**Request**
```json
{ "description": "BMW X1 2022, pacote M", "mileage_km": 22000, "region": "SP" }
```

**Response**
```json
{ "min_price": 76000, "max_price": 84000, "rationale": "Estimativa baseada em históricos regionais e condição informada." }
```

---

## Lovable Integration Checklist
1. **Health check**: call `GET /health` on startup.
2. **Auth (optional)**: if you require user tokens, call `/v1/auth/register` and `/v1/auth/login`.
3. **Search flow**:
   - Start with `POST /v1/search` to get `session_id`.
   - Use `POST /v1/axis-bot/chat` to drive the conversational recommendation.
4. **Browse inventory**:
   - Use `GET /v1/opportunities?region=SP` for curated listings.
   - Use `GET /v1/listings/{id}` for detail.
   - Use `GET /v1/trusted-sellers` to display marketplace trust signals.
5. **Selling flow**: use `POST /v1/sell/estimate`.
6. **Docs & schema**: consume `/openapi.json` to auto-generate clients.
