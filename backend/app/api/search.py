from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.listing import AxisBotMessage, AxisBotReply, SearchRequest, SearchResponse
from app.services.recommendations import AxisBotService

router = APIRouter(prefix="/v1", tags=["search"])

bot_service = AxisBotService()


@router.post("/search", response_model=SearchResponse)
def start_search(payload: SearchRequest, db: Session = Depends(get_db)) -> SearchResponse:  # noqa: ARG001
    session_id = bot_service.start_session(payload.query)
    return SearchResponse(session_id=session_id)


@router.post("/axis-bot/chat", response_model=AxisBotReply)
def axis_bot_chat(message: AxisBotMessage, db: Session = Depends(get_db)) -> AxisBotReply:
    return bot_service.handle_message(db, message.session_id, message.message)
