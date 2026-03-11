"""add product_name to order_items

Revision ID: d6e8f9a1b2c3
Revises: c5d7e8f9a0b1
Create Date: 2026-03-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "d6e8f9a1b2c3"
down_revision = "c5d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add product_name column to order_items with a default so existing rows are valid
    op.add_column(
        "order_items",
        sa.Column("product_name", sa.String(200), nullable=False, server_default=""),
    )
    # Back-fill existing rows from the products table
    op.execute(
        """
        UPDATE order_items
        SET product_name = p.name
        FROM products p
        WHERE order_items.product_id = p.id
          AND order_items.product_name = ''
        """
    )
    # Remove the server default after back-fill
    op.alter_column("order_items", "product_name", server_default=None)


def downgrade() -> None:
    op.drop_column("order_items", "product_name")
