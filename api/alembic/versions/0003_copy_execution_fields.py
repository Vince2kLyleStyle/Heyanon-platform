"""add execution fields notional_usd and copied_qty, add unique index

Revision ID: 0003_copy_execution_fields
Revises: 0002_add_copy_tables
Create Date: 2025-10-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_copy_execution_fields'
down_revision = '0002_add_copy_tables'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('copy_subscribers', sa.Column('max_notional_usd', sa.Float(), nullable=True))
    op.add_column('copy_executions', sa.Column('notional_usd', sa.Float(), nullable=True))
    op.add_column('copy_executions', sa.Column('copied_qty', sa.Float(), nullable=True))
    op.create_index('uq_copy_execution_signal', 'copy_executions', ['strategy_id', 'subscriber_id', 'signal_trade_id'], unique=True)


def downgrade():
    op.drop_index('uq_copy_execution_signal', 'copy_executions')
    op.drop_column('copy_executions', 'copied_qty')
    op.drop_column('copy_executions', 'notional_usd')
    op.drop_column('copy_subscribers', 'max_notional_usd')
