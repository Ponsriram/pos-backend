"""
ORM model package.

Import all models here so Alembic auto-generates migrations correctly.
"""

from app.models.users import User, UserPermission  # noqa: F401
from app.models.stores import (  # noqa: F401
    Chain, Store, POSTerminal, Employee, DineInTable, OrderTableLink, Expense,
)
from app.models.products import Category, Product  # noqa: F401
from app.models.orders import Order, OrderItem, Payment  # noqa: F401
from app.models.menus import Menu, MenuItem, MenuSchedule, MenuPricingRule  # noqa: F401
from app.models.inventory import (  # noqa: F401
    InventoryUnit, InventoryLocation, InventoryItem, StockLevel,
    StockAdjustment, Recipe, RecipeLine, StockTransfer, StockTransferLine,
)
from app.models.purchasing import (  # noqa: F401
    Vendor, PurchaseOrder, PurchaseOrderLine,
    PurchaseReceipt, PurchaseReceiptLine,
)
from app.models.delivery import DeliveryOrderDetails  # noqa: F401
from app.models.shifts import Shift, ShiftPaymentSummary, DayClose  # noqa: F401
from app.models.integrations import (  # noqa: F401
    AggregatorConfig, AggregatorStoreLink, AggregatorOrder,
)
from app.models.guests import Guest  # noqa: F401
from app.models.billing import KOT, KOTItem, Invoice, BillTemplate  # noqa: F401
from app.models.ledger import (  # noqa: F401
    TaxGroup, TaxRule, CityLedgerAccount, CityLedgerTransaction,
)
from app.models.audit import AuditLog  # noqa: F401
from app.models.marketing import Campaign  # noqa: F401
