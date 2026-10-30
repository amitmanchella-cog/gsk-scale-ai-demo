import math

from app import data
from app.forecast import forecast_consumption
from app.models import Product


def test_product_default_lead_time_is_six_weeks():
    assert Product.model_fields["lead_time_weeks"].default == 6
    assert Product(product_id="X", name="x", dosage_form="tablet").lead_time_weeks == 6
    assert data.PRODUCTS_BY_ID["IP-100"].lead_time_weeks == 6


def _expected(site_id: str, product_id: str) -> tuple[bool, int]:
    history = [p.quantity for p in data.CONSUMPTION[(site_id, product_id)]]
    weekly = forecast_consumption(history, weeks=1)[0]
    on_hand = next(s.stock_on_hand for s in data.STOCK if s.site_id == site_id and s.product_id == product_id)
    reorder_point = weekly * data.PRODUCTS_BY_ID[product_id].lead_time_weeks
    recommend = on_hand < reorder_point
    return recommend, math.ceil(reorder_point - on_hand) if recommend else 0


def test_reorder_for_one_site_matches_formula(client):
    r = client.get("/reorder", params={"site_id": "S001"})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == len(data.PRODUCTS)
    for rec in body:
        recommend, qty = _expected("S001", rec["product_id"])
        assert rec["recommend"] is recommend
        assert rec["recommended_qty"] == qty
        assert rec["reorder_point"] == round(rec["forecast_weekly_consumption"] * rec["lead_time_weeks"], 2)


def test_seeded_dataset_has_both_outcomes(client):
    body = client.get("/reorder").json()
    assert len(body) == len(data.SITES) * len(data.PRODUCTS)
    flags = {rec["recommend"] for rec in body}
    assert flags == {True, False}


def test_reorder_unknown_site_404(client):
    assert client.get("/reorder", params={"site_id": "NOPE"}).status_code == 404
