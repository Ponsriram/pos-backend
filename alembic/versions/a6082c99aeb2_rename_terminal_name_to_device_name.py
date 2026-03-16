"""rename_terminal_name_to_device_name

Revision ID: a6082c99aeb2
Revises: e7f0a1b2c3d4
Create Date: 2026-03-15 15:12:36.190119
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a6082c99aeb2'
down_revision: Union[str, None] = 'e7f0a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Migrate legacy terminal columns to the current model shape.
    op.alter_column(
        'pos_terminals',
        'terminal_name',
        new_column_name='device_name',
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )
    op.alter_column(
        'pos_terminals',
        'device_id',
        new_column_name='device_identifier',
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )

    op.drop_constraint('uq_pos_terminals_device_id', 'pos_terminals', type_='unique')
    op.drop_index('ix_pos_terminals_device_id', table_name='pos_terminals')

    op.drop_column('pos_terminals', 'terminal_secret')
    op.drop_column('pos_terminals', 'terminal_type')

    op.create_index('ix_pos_terminals_device_identifier', 'pos_terminals', ['device_identifier'], unique=False)
    op.create_unique_constraint('uq_pos_terminals_device_identifier', 'pos_terminals', ['device_identifier'])


def downgrade() -> None:
    op.drop_constraint('uq_pos_terminals_device_identifier', 'pos_terminals', type_='unique')
    op.drop_index('ix_pos_terminals_device_identifier', table_name='pos_terminals')

    op.add_column('pos_terminals', sa.Column('terminal_secret', sa.String(length=255), nullable=False, server_default=sa.text("'legacy-secret'")))
    op.add_column('pos_terminals', sa.Column('terminal_type', sa.String(length=20), nullable=False, server_default=sa.text("'legacy'")))

    op.alter_column(
        'pos_terminals',
        'device_identifier',
        new_column_name='device_id',
        existing_type=sa.String(length=255),
        existing_nullable=False,
    )
    op.alter_column(
        'pos_terminals',
        'device_name',
        new_column_name='terminal_name',
        existing_type=sa.String(length=120),
        existing_nullable=False,
    )

    op.create_index('ix_pos_terminals_device_id', 'pos_terminals', ['device_id'], unique=False)
    op.create_unique_constraint('uq_pos_terminals_device_id', 'pos_terminals', ['device_id'])
