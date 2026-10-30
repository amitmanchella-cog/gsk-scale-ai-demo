"""Deterministic synthetic dataset: sites, products, stock, consumption history and shipments."""

import random
from datetime import date, timedelta

from app.models import ConsumptionPoint, Product, Shipment, Site, StockLevel

SEED = 42
HISTORY_WEEKS = 26
LAST_WEEK_START = date(2026, 3, 23)  # a Monday; history is the 26 weeks ending here

SITES: list[Site] = [
    Site(site_id="S001", name="Boston General", country="US", region="US", timezone="America/New_York"),
    Site(site_id="S002", name="Chicago Research Hospital", country="US", region="US", timezone="America/Chicago"),
    Site(site_id="S003", name="San Diego Clinical Centre", country="US", region="US", timezone="America/Los_Angeles"),
    Site(site_id="S004", name="London Royal Infirmary", country="GB", region="EU", timezone="Europe/London"),
    Site(site_id="S005", name="Berlin Charité Trials Unit", country="DE", region="EU", timezone="Europe/Berlin"),
    Site(site_id="S006", name="Madrid Clinical Institute", country="ES", region="EU", timezone="Europe/Madrid"),
    Site(site_id="S007", name="Tokyo Medical University", country="JP", region="APAC", timezone="Asia/Tokyo"),
    Site(site_id="S008", name="Sydney Trials Network", country="AU", region="APAC", timezone="Australia/Sydney"),
]

PRODUCTS: list[Product] = [
    Product(product_id="IP-100", name="Investigational Product 100", dosage_form="tablet"),
    Product(product_id="IP-200", name="Investigational Product 200", dosage_form="capsule"),
    Product(product_id="IP-300", name="Investigational Product 300", dosage_form="vial", lead_time_weeks=8),
    Product(product_id="IP-400", name="Investigational Product 400", dosage_form="prefilled syringe"),
    Product(product_id="IP-500", name="Investigational Product 500", dosage_form="tablet", lead_time_weeks=4),
    Product(product_id="PBO-001", name="Matching Placebo", dosage_form="tablet"),
]


def _build() -> tuple[dict[tuple[str, str], list[ConsumptionPoint]], list[StockLevel]]:
    rng = random.Random(SEED)
    first_week = LAST_WEEK_START - timedelta(weeks=HISTORY_WEEKS - 1)
    consumption: dict[tuple[str, str], list[ConsumptionPoint]] = {}
    stock: list[StockLevel] = []
    for site in SITES:
        for product in PRODUCTS:
            base = rng.randint(8, 60)
            drift = rng.uniform(-0.6, 0.9)
            points = []
            for i in range(HISTORY_WEEKS):
                qty = max(0, round(base + drift * i + rng.gauss(0, base * 0.15)))
                points.append(ConsumptionPoint(week_start=first_week + timedelta(weeks=i), quantity=qty))
            consumption[(site.site_id, product.product_id)] = points
            # Hold between 2 and 10 weeks of cover so some pairs trip the reorder rule and others do not.
            weeks_of_cover = rng.uniform(2, 10)
            stock.append(
                StockLevel(
                    site_id=site.site_id,
                    product_id=product.product_id,
                    stock_on_hand=round(base * weeks_of_cover),
                    as_of=LAST_WEEK_START,
                )
            )
    return consumption, stock


CONSUMPTION, STOCK = _build()
SHIPMENTS: list[Shipment] = []

SITES_BY_ID = {s.site_id: s for s in SITES}
PRODUCTS_BY_ID = {p.product_id: p for p in PRODUCTS}


def reset_shipments() -> None:
    """Clear in-memory shipments (used by tests)."""
    SHIPMENTS.clear()
