def test_shipments_start_empty(client):
    assert client.get("/shipments").json() == []


def test_create_and_list_shipment_round_trip(client):
    payload = {"site_id": "S007", "product_id": "IP-300", "quantity": 120, "planned_arrival": "2026-04-13"}
    r = client.post("/shipments", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["shipment_id"] == 1
    assert created["status"] == "planned"
    assert {k: created[k] for k in payload} == payload

    listed = client.get("/shipments").json()
    assert listed == [created]

    second = client.post("/shipments", json={"site_id": "S001", "product_id": "IP-100", "quantity": 10})
    assert second.json()["shipment_id"] == 2
    assert len(client.get("/shipments").json()) == 2


def test_create_shipment_unknown_site_or_product_404(client):
    assert client.post("/shipments", json={"site_id": "NOPE", "product_id": "IP-100", "quantity": 5}).status_code == 404
    assert client.post("/shipments", json={"site_id": "S001", "product_id": "NOPE", "quantity": 5}).status_code == 404


def test_create_shipment_invalid_payload_422(client):
    assert client.post("/shipments", json={"site_id": "S001", "product_id": "IP-100", "quantity": 0}).status_code == 422
    assert client.post("/shipments", json={"site_id": "S001"}).status_code == 422
