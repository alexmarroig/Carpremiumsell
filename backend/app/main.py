from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, health, listings, search, sell
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.core.rate_limit import get_rate_limiter

setup_logging()
settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")

origins = [origin.strip() for origin in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    limiter = get_rate_limiter()
    limiter(request)
    return await call_next(request)


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(listings.router)
app.include_router(search.router)
app.include_router(sell.router)
