from app.services.trust import TrustSignals, trust_badge


def test_trust_badge_awards_verified():
    signals = TrustSignals(seller_type="dealer", has_photos=True, price_deviation=-0.05, listing_age_hours=12)
    assert trust_badge(signals) == "Verified listing"


def test_trust_badge_selected():
    signals = TrustSignals(seller_type="dealer", has_photos=False, price_deviation=-0.3, listing_age_hours=1)
    assert trust_badge(signals) == "Selected by AXIS"
