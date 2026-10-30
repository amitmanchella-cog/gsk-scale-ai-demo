# supply_api — clinical supply forecast service (UC3)

A small FastAPI service that forecasts weekly investigational-product consumption per clinical trial site and recommends reorders before a site runs out. It is the UC3 service in this demo kit: its pytest suite is the thing the CI self-heal Automation watches, so a red build here is what Devin diagnoses and fixes live.

Synthetic, deterministic in-memory data only (`random.Random(42)`): 8 sites across US/EU/APAC with real IANA timezones, 6 investigational products, stock per site/product and 26 weeks of weekly consumption history. No database, no real GSK data.

## Run

```bash
pip install -r services/supply_api/requirements.txt
uvicorn app.main:app --reload --app-dir services/supply_api
```

Interactive docs: http://127.0.0.1:8000/docs

## Test

From the repo root:

```bash
pytest services/supply_api
```

`tests/conftest.py` puts `services/supply_api` on `sys.path`, so tests simply `from app.main import app`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | `{"status": "ok", "version": ...}` |
| GET | `/sites` | List trial sites |
| GET | `/sites/{site_id}` | Site detail (404 if unknown) |
| GET | `/products` | List investigational products (each has `lead_time_weeks`, default 6) |
| GET | `/stock?site_id=&product_id=` | Stock on hand, optional filters |
| GET | `/consumption/{site_id}/{product_id}?weeks=N` | Most recent N weeks of consumption |
| GET | `/forecast/{site_id}/{product_id}?weeks=4&method=moving_average\|linear_trend` | N weekly forecasts |
| GET | `/reorder?site_id=` | Recommend when `stock_on_hand < forecast_weekly_consumption * lead_time_weeks`, with `recommended_qty` |
| GET / POST | `/shipments` | List / create in-memory shipments (201, status `planned`) |
| GET | `/reports/consumption?start=&end=&site_id=` | Date-range totals; ISO datetimes with offsets or `Z` are converted to each site's local date before weeks are selected |

## Layout

```
app/main.py      FastAPI app and endpoints
app/models.py    Pydantic v2 models
app/data.py      Seeded synthetic dataset
app/forecast.py  moving_average, linear_trend, forecast_consumption
app/dates.py     zoneinfo-based ISO parsing and week helpers
tests/           pytest + TestClient, one file per concern
```
