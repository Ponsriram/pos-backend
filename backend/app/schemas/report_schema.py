"""Pydantic schemas for Analytics & Reporting endpoints."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReportDateRange(BaseModel):
    start_date: date
    end_date: date


# ── Sales Report ──────────────────────────────────────────────────────────

class SalesReportRow(BaseModel):
    date: date
    total_orders: int
    gross_sales: float
    total_tax: float
    total_discounts: float
    total_service_charge: float
    total_tips: float
    net_sales: float


class SalesReport(BaseModel):
    store_id: UUID
    start_date: date
    end_date: date
    rows: list[SalesReportRow]
    summary: "SalesReportSummary"


class SalesReportSummary(BaseModel):
    total_orders: int
    gross_sales: float
    total_tax: float
    total_discounts: float
    total_service_charge: float
    total_tips: float
    net_sales: float


# ── Product Mix ───────────────────────────────────────────────────────────

class ProductMixRow(BaseModel):
    product_id: UUID
    product_name: str
    category: str | None
    quantity_sold: int
    gross_revenue: float
    percentage_of_total: float


class ProductMixReport(BaseModel):
    store_id: UUID
    start_date: date
    end_date: date
    rows: list[ProductMixRow]


# ── Payment Summary ───────────────────────────────────────────────────────

class PaymentMethodSummaryRow(BaseModel):
    payment_method: str
    transaction_count: int
    total_amount: float
    tip_amount: float
    refund_amount: float


class PaymentSummaryReport(BaseModel):
    store_id: UUID
    start_date: date
    end_date: date
    rows: list[PaymentMethodSummaryRow]


# ── Hourly Sales ──────────────────────────────────────────────────────────

class HourlySalesRow(BaseModel):
    hour: int = Field(..., ge=0, le=23)
    total_orders: int
    net_sales: float


class HourlySalesReport(BaseModel):
    store_id: UUID
    report_date: date
    rows: list[HourlySalesRow]


# ── Employee Performance ─────────────────────────────────────────────────

class EmployeePerformanceRow(BaseModel):
    employee_id: UUID
    employee_name: str
    total_orders: int
    net_sales: float
    average_order_value: float
    total_tips: float


class EmployeePerformanceReport(BaseModel):
    store_id: UUID
    start_date: date
    end_date: date
    rows: list[EmployeePerformanceRow]


# ── Inventory Valuation ──────────────────────────────────────────────────

class InventoryValuationRow(BaseModel):
    item_id: UUID
    item_name: str
    category: str | None
    unit: str
    quantity_on_hand: float
    average_cost: float
    total_value: float


class InventoryValuationReport(BaseModel):
    store_id: UUID
    rows: list[InventoryValuationRow]
    total_value: float


# ── Tax Report ────────────────────────────────────────────────────────────

class TaxReportRow(BaseModel):
    tax_name: str
    rate: float
    taxable_amount: float
    tax_collected: float


class TaxReport(BaseModel):
    store_id: UUID
    start_date: date
    end_date: date
    rows: list[TaxReportRow]
    total_taxable: float
    total_tax: float
