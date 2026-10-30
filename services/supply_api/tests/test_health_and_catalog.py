from app import __version__, data


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


def test_list_sites(client):
    r = client.get("/sites")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 8
    assert {s["region"] for s in body} == {"US", "EU", "APAC"}
    assert all(s["timezone"] for s in body)


def test_get_site(client):
    r = client.get("/sites/S007")
    assert r.status_code == 200
    assert r.json()["timezone"] == "Asia/Tokyo"


def test_get_site_unknown_404(client):
    assert client.get("/sites/NOPE").status_code == 404


def test_list_products(client):
    r = client.get("/products")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 6
    assert {p["product_id"] for p in body} == set(data.PRODUCTS_BY_ID)


def test_stock_unfiltered_and_filtered(client):
    everything = client.get("/stock").json()
    assert len(everything) == len(data.SITES) * len(data.PRODUCTS)

    by_site = client.get("/stock", params={"site_id": "S001"}).json()
    assert len(by_site) == len(data.PRODUCTS)
    assert all(s["site_id"] == "S001" for s in by_site)

    one = client.get("/stock", params={"site_id": "S001", "product_id": "IP-100"}).json()
    assert len(one) == 1
    assert one[0]["stock_on_hand"] >= 0


def test_stock_unknown_filter_404(client):
    assert client.get("/stock", params={"site_id": "NOPE"}).status_code == 404
    assert client.get("/stock", params={"product_id": "NOPE"}).status_code == 404


def test_consumption_history_most_recent_weeks(client):
    r = client.get("/consumption/S001/IP-100", params={"weeks": 4})
    assert r.status_code == 200
    body = r.json()
    assert body["site_id"] == "S001" and body["product_id"] == "IP-100"
    assert len(body["weeks"]) == 4
    assert body["weeks"][-1]["week_start"] == data.LAST_WEEK_START.isoformat()
    assert [w["week_start"] for w in body["weeks"]] == sorted(w["week_start"] for w in body["weeks"])


def test_consumption_defaults_to_full_history(client):
    assert len(client.get("/consumption/S001/IP-100").json()["weeks"]) == data.HISTORY_WEEKS


def test_consumption_validation(client):
    assert client.get("/consumption/S001/NOPE").status_code == 404
    assert client.get("/consumption/S001/IP-100", params={"weeks": 0}).status_code == 422
