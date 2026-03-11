"""backfill kot_items product names from UUIDs to actual names

Revision ID: e7f0a1b2c3d4
Revises: d6e8f9a1b2c3
Create Date: 2026-03-11 00:00:01.000000

"""
from alembic import op

# revision identifiers
revision = "e7f0a1b2c3d4"
down_revision = "d6e8f9a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update kot_items that have UUID-like product_name values
    # by resolving the actual product name through order_items → products
    op.execute(
        """
        UPDATE kot_items
        SET product_name = p.name
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE kot_items.order_item_id = oi.id
          AND kot_items.product_name ~ '^[0-9a-f]{8}-[0-9a-f]{4}-'
        """
    )


def downgrade() -> None:
    # Not reversible – product names stay as-is
    pass
