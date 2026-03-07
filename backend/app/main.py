"""
FastAPI application entry point.

- Registers all routers
- Configures CORS (open for development; tighten in production)
- Provides a health-check endpoint
- Generates interactive Swagger docs at /docs
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.routers import (
    auth_routes,
    store_routes,
    employee_routes,
    product_routes,
    order_routes,
    analytics_routes,
    menu_routes,
    inventory_routes,
    purchasing_routes,
    delivery_routes,
    shift_routes,
    billing_routes,
    guest_routes,
    ledger_routes,
    integration_routes,
    marketing_routes,
    audit_routes,
)

settings = get_settings()


# ── Lifespan: create tables on startup (dev convenience) ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: ensure all tables exist (useful for first run / dev).
    In production, rely on Alembic migrations instead.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


# ── App factory ───────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-grade REST API for a multi-tenant restaurant POS SaaS platform.\n\n"
        "Supports:\n"
        "- Multi-store & chain management per owner\n"
        "- Menu & pricing management with schedules\n"
        "- Product/category catalogue\n"
        "- Order lifecycle, status transitions & payments\n"
        "- Table management, merges, transfers\n"
        "- Delivery management & aggregator integrations\n"
        "- Kitchen order tickets (KOT) & invoicing\n"
        "- Shift management & day-close reports\n"
        "- Inventory, recipes, stock transfers & purchasing\n"
        "- Tax groups, city ledger & accounting\n"
        "- Guest CRM & loyalty\n"
        "- Marketing campaigns\n"
        "- Offline POS sync\n"
        "- Analytical dashboard & reporting\n"
        "- Audit logging"
    ),
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc alternative
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(store_routes.router)
app.include_router(employee_routes.router)
app.include_router(product_routes.router)
app.include_router(order_routes.router)
app.include_router(analytics_routes.router)
app.include_router(menu_routes.router)
app.include_router(inventory_routes.router)
app.include_router(purchasing_routes.router)
app.include_router(delivery_routes.router)
app.include_router(shift_routes.router)
app.include_router(billing_routes.router)
app.include_router(guest_routes.router)
app.include_router(ledger_routes.router)
app.include_router(integration_routes.router)
app.include_router(marketing_routes.router)
app.include_router(audit_routes.router)


# ── Health check ──────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}
