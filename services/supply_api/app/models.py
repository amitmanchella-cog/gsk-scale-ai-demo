"""Pydantic v2 models for the clinical supply forecast API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ForecastMethod = Literal["moving_average", "linear_trend"]


class Health(BaseModel):
    status: str
    version: str


class Site(BaseModel):
    model_config = ConfigDict(frozen=True)

    site_id: str
    name: str
    country: str
    region: Literal["US", "EU", "APAC"]
    timezone: str = Field(description="IANA timezone name, e.g. Asia/Tokyo")


class Product(BaseModel):
    model_config = ConfigDict(frozen=True)

    product_id: str
    name: str
    dosage_form: str
    lead_time_weeks: int = Field(default=6, ge=1, description="Weeks from order to arrival at site")


class StockLevel(BaseModel):
    site_id: str
    product_id: str
    stock_on_hand: int = Field(ge=0)
    as_of: date


class ConsumptionPoint(BaseModel):
    week_start: date
    quantity: int = Field(ge=0)


class ConsumptionHistory(BaseModel):
    site_id: str
    product_id: str
    weeks: list[ConsumptionPoint]


class ForecastPoint(BaseModel):
    week_start: date
    quantity: float = Field(ge=0)


class Forecast(BaseModel):
    site_id: str
    product_id: str
    method: ForecastMethod
    weeks: list[ForecastPoint]


class ReorderRecommendation(BaseModel):
    site_id: str
    product_id: str
    stock_on_hand: int
    forecast_weekly_consumption: float
    lead_time_weeks: int
    reorder_point: float = Field(description="forecast_weekly_consumption * lead_time_weeks")
    recommend: bool
    recommended_qty: int = Field(ge=0)


class ShipmentCreate(BaseModel):
    site_id: str
    product_id: str
    quantity: int = Field(gt=0)
    planned_arrival: date | None = None


class Shipment(ShipmentCreate):
    shipment_id: int
    status: Literal["planned", "in_transit", "delivered"] = "planned"


class ConsumptionReportLine(BaseModel):
    site_id: str
    product_id: str
    start_local_date: date
    end_local_date: date
    weeks_included: int
    total_quantity: int


class ConsumptionReport(BaseModel):
    start: str
    end: str
    lines: list[ConsumptionReportLine]
