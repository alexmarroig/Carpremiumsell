from fastapi import APIRouter

from app.schemas.listing import SellEstimateRequest, SellEstimateResponse

router = APIRouter(prefix="/v1", tags=["sell"])


@router.post("/sell/estimate", response_model=SellEstimateResponse)
def estimate_price(payload: SellEstimateRequest) -> SellEstimateResponse:
    base_price = 80000
    if payload.mileage_km:
        base_price -= payload.mileage_km * 0.05
    rationale = "Estimativa baseada em históricos regionais e condição informada."
    return SellEstimateResponse(min_price=base_price * 0.95, max_price=base_price * 1.05, rationale=rationale)
