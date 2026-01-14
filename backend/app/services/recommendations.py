import uuid
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.listing import NormalizedListing
from app.schemas.listing import AxisBotReply
from .ai_provider import AIProvider, MockProvider
from .listing_selection import select_cheapest_with_reputation
from .pricing import compute_regional_market_stats, detect_opportunity
from .trust import TrustSignals, trust_badge


class AxisBotSession:
    def __init__(self, session_id: str, context: Dict):
        self.session_id = session_id
        self.context = context
        self.turns = 0


class AxisBotService:
    def __init__(self, ai_provider: Optional[AIProvider] = None) -> None:
        self.ai_provider = ai_provider or MockProvider()
        self.sessions: Dict[str, AxisBotSession] = {}

    def start_session(self, query: str) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = AxisBotSession(session_id, {"query": query})
        return session_id

    def handle_message(self, db: Session, session_id: str, message: str) -> AxisBotReply:
        session = self.sessions.get(session_id)
        if not session:
            session = AxisBotSession(session_id, {"query": message})
            self.sessions[session_id] = session

        session.turns += 1
        messages = [
            {"role": "system", "content": "Você é o Axis Bot, um concierge automotivo."},
            {"role": "user", "content": session.context.get("query", "")},
            {"role": "user", "content": message},
        ]
        response_text = self.ai_provider.chat(messages)

        listing = self._pick_listing(db)
        badge = None
        if listing:
            market = compute_regional_market_stats(
                db, region_key=listing.state or "*", brand=listing.brand, model=listing.model
            )
            badge = detect_opportunity(listing.final_price_brl or listing.price_brl or 0, market)
            badge = badge or trust_badge(TrustSignals(seller_type=listing.seller_type, has_photos=bool(listing.photos)))

        return AxisBotReply(
            reply=f"{response_text}. Selecionamos uma opção premium para você.",
            listing=listing,
        )

    def _pick_listing(self, db: Session) -> Optional[NormalizedListing]:
        return select_cheapest_with_reputation(db)
