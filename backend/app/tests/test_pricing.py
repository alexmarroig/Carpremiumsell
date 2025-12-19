from app.services.pricing import apply_markup, compute_opportunity_badge


def test_apply_markup_mid_category():
    assert apply_markup(100000, "mid") == 108500.0


def test_compute_opportunity_badge():
    badge = compute_opportunity_badge(90000, median=100000, p25=95000)
    assert badge == "Selected by AXIS"
