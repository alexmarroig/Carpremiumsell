# API Surface

## Health
- `GET /health` -> `{ "status": "ok" }`

## Auth
- `POST /v1/auth/register` {email, password}
- `POST /v1/auth/login` {email, password} -> JWT bearer token

## Listings
- `GET /v1/opportunities?region=SP` -> curated listings with badges
- `GET /v1/listings/{id}` -> listing detail

## Search & Axis Bot
- `POST /v1/search` {query, preferences?} -> `{session_id}`
- `POST /v1/axis-bot/chat` {session_id, message} -> reply + single listing

## Sell Estimate
- `POST /v1/sell/estimate` {description, mileage_km?, region?} -> price range

### Notes
- All responses are JSON and mobile-friendly.
- Axis Bot replies in Portuguese with premium tone and single recommendation.
- Trust badges exposed: `Verified listing` or `Selected by AXIS`.
