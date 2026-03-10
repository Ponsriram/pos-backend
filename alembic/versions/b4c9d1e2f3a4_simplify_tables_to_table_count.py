"""simplify tables to table_count

Revision ID: b4c9d1e2f3a4
Revises: 52054d60432c, a3b8c9d0e1f2
Create Date: 2026-03-10 00:00:00.000000

Changes:
- Merge heads 52054d60432c and a3b8c9d0e1f2
- Add table_count column to stores table
- Remove orders.table_id FK and replace with orders.table_number
- Drop order_table_links table
- Drop dine_in_tables table
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b4c9d1e2f3a4"
down_revision = ("52054d60432c", "a3b8c9d0e1f2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add table_count to stores
    op.add_column(
        "stores",
        sa.Column("table_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # 2. Replace orders.table_id with orders.table_number
    #    First drop the FK constraint and column, then add the new column
    op.drop_constraint(
        "orders_table_id_fkey", "orders", type_="foreignkey"
    )
    op.drop_column("orders", "table_id")
    op.add_column(
        "orders",
        sa.Column("table_number", sa.Integer(), nullable=True),
    )

    # 3. Drop order_table_links table
    op.drop_index("ix_order_table_links_order_id", table_name="order_table_links")
    op.drop_index("ix_order_table_links_table_id", table_name="order_table_links")
    op.drop_table("order_table_links")

    # 4. Drop dine_in_tables table
    op.drop_index("ix_dine_in_tables_store_id", table_name="dine_in_tables")
    op.drop_index("ix_dine_in_tables_status", table_name="dine_in_tables")
    op.drop_table("dine_in_tables")


def downgrade() -> None:
    # Recreate dine_in_tables
    op.create_table(
        "dine_in_tables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("table_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(50), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default=sa.text("4")),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'available'")),
        sa.Column("section", sa.String(50), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("position_x", sa.Integer(), nullable=True),
        sa.Column("position_y", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_dine_in_tables_store_id", "dine_in_tables", ["store_id"], unique=False)
    op.create_index("ix_dine_in_tables_status", "dine_in_tables", ["status"], unique=False)

    # Recreate order_table_links
    op.create_table(
        "order_table_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("table_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dine_in_tables.id", ondelete="CASCADE"), nullable=False),
    )
    op.create_index("ix_order_table_links_order_id", "order_table_links", ["order_id"], unique=False)
    op.create_index("ix_order_table_links_table_id", "order_table_links", ["table_id"], unique=False)

    # Restore orders.table_id and drop orders.table_number
    op.drop_column("orders", "table_number")
    op.add_column(
        "orders",
        sa.Column("table_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "orders_table_id_fkey", "orders", "dine_in_tables",
        ["table_id"], ["id"], ondelete="SET NULL",
    )

    # Drop table_count from stores
    op.drop_column("stores", "table_count")
