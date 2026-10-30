"""FastAPI application for the UC3 clinical supply forecast service."""

import math
from datetime import timedelta

from fastapi import FastAPI, HTTPException, Query

from app import __version__, data
from app.dates import date_range_weeks, parse_iso_datetime, to_site_local_date
from app.forecast import forecast_consumption
from app.models import (
    ConsumptionHistory,
    ConsumptionReport,
    ConsumptionReportLine,
    Forecast,
    ForecastMethod,
    ForecastPoint,
    Health,
    Product,
    ReorderRecommendation,
    Shipment,
    ShipmentCreate,
    Site,
    StockLevel,
)

app = FastAPI(title="Clinical Supply Forecast API", version=__version__)


def _get_site(site_id: str) -> Site:
    site = data.SITES_BY_ID.get(site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"unknown site {site_id!r}")
    return site


def _get_product(product_id: str) -> Product:
    product = data.PRODUCTS_BY_ID.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"unknown product {product_id!r}")
    return product


def _history(site_id: str, product_id: str) -> list[int]:
    return [p.quantity for p in data.CONSUMPTION[(site_id, product_id)]]


def _stock_on_hand(site_id: str, product_id: str) -> int:
    return next(s.stock_on_hand for s in data.STOCK if s.site_id == site_id and s.product_id == product_id)


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", version=__version__)


@app.get("/sites", response_model=list[Site])
def list_sites() -> list[Site]:
    return data.SITES


@app.get("/sites/{site_id}", response_model=Site)
def get_site(site_id: str) -> Site:
    return _get_site(site_id)


@app.get("/products", response_model=list[Product])
def list_products() -> list[Product]:
    return data.PRODUCTS


@app.get("/stock", response_model=list[StockLevel])
def list_stock(site_id: str | None = None, product_id: str | None = None) -> list[StockLevel]:
    if site_id is not None:
        _get_site(site_id)
    if product_id is not None:
        _get_product(product_id)
    return [
        s
        for s in data.STOCK
        if (site_id is None or s.site_id == site_id) and (product_id is None or s.product_id == product_id)
    ]


@app.get("/consumption/{site_id}/{product_id}", response_model=ConsumptionHistory)
def get_consumption(
    site_id: str, product_id: str, weeks: int = Query(default=data.HISTORY_WEEKS, ge=1, le=data.HISTORY_WEEKS)
) -> ConsumptionHistory:
    _get_site(site_id)
    _get_product(product_id)
    points = data.CONSUMPTION[(site_id, product_id)][-weeks:]
    return ConsumptionHistory(site_id=site_id, product_id=product_id, weeks=points)


@app.get("/forecast/{site_id}/{product_id}", response_model=Forecast)
def get_forecast(
    site_id: str,
    product_id: str,
    weeks: int = Query(default=4, ge=1, le=52),
    method: ForecastMethod = "moving_average",
) -> Forecast:
    _get_site(site_id)
    _get_product(product_id)
    values = forecast_consumption(_history(site_id, product_id), weeks, method)
    next_week = data.LAST_WEEK_START + timedelta(weeks=1)
    points = [ForecastPoint(week_start=next_week + timedelta(weeks=i), quantity=q) for i, q in enumerate(values)]
    return Forecast(site_id=site_id, product_id=product_id, method=method, weeks=points)


@app.get("/reorder", response_model=list[ReorderRecommendation])
def reorder(site_id: str | None = None) -> list[ReorderRecommendation]:
    sites = [_get_site(site_id)] if site_id is not None else data.SITES
    recommendations = []
    for site in sites:
        for product in data.PRODUCTS:
            weekly = forecast_consumption(_history(site.site_id, product.product_id), weeks=1)[0]
            on_hand = _stock_on_hand(site.site_id, product.product_id)
            reorder_point = weekly * product.lead_time_weeks
            recommend = on_hand < reorder_point
            recommendations.append(
                ReorderRecommendation(
                    site_id=site.site_id,
                    product_id=product.product_id,
                    stock_on_hand=on_hand,
                    forecast_weekly_consumption=weekly,
                    lead_time_weeks=product.lead_time_weeks,
                    reorder_point=round(reorder_point, 2),
                    recommend=recommend,
                    recommended_qty=math.ceil(reorder_point - on_hand) if recommend else 0,
                )
            )
    return recommendations


@app.get("/shipments", response_model=list[Shipment])
def list_shipments() -> list[Shipment]:
    return data.SHIPMENTS


@app.post("/shipments", response_model=Shipment, status_code=201)
def create_shipment(payload: ShipmentCreate) -> Shipment:
    _get_site(payload.site_id)
    _get_product(payload.product_id)
    shipment = Shipment(shipment_id=len(data.SHIPMENTS) + 1, status="planned", **payload.model_dump())
    data.SHIPMENTS.append(shipment)
    return shipment


@app.get("/reports/consumption", response_model=ConsumptionReport)
def consumption_report(start: str, end: str, site_id: str | None = None) -> ConsumptionReport:
    try:
        start_dt, end_dt = parse_iso_datetime(start), parse_iso_datetime(end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if start_dt > end_dt:
        raise HTTPException(status_code=422, detail="start must be on or before end")

    sites = [_get_site(site_id)] if site_id is not None else data.SITES
    lines = []
    for site in sites:
        start_local = to_site_local_date(start_dt, site.timezone)
        end_local = to_site_local_date(end_dt, site.timezone)
        selected = set(date_range_weeks(start_local, end_local))
        for product in data.PRODUCTS:
            points = [p for p in data.CONSUMPTION[(site.site_id, product.product_id)] if p.week_start in selected]
            lines.append(
                ConsumptionReportLine(
                    site_id=site.site_id,
                    product_id=product.product_id,
                    start_local_date=start_local,
                    end_local_date=end_local,
                    weeks_included=len(points),
                    total_quantity=sum(p.quantity for p in points),
                )
            )
    return ConsumptionReport(start=start, end=end, lines=lines)
