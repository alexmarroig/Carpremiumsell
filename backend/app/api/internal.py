from fastapi import APIRouter
from pydantic import BaseModel
from redis import Redis
from rq import Queue

from app.core.config import get_settings
from app.workers import jobs

router = APIRouter(prefix="/internal", tags=["internal"])


class IngestRequest(BaseModel):
    region_key: str
    query_text: str | None = None
    limit: int | None = 30


@router.post("/ingest/{source_name}")
def ingest_source(source_name: str, request: IngestRequest):
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    queue = Queue("axis", connection=redis_conn)
    job = queue.enqueue(
        jobs.ingest_marketplace,
        source_name,
        request.region_key,
        request.query_text,
        request.limit or 30,
    )
    return {"enqueued": True, "job_id": job.id}
