"""create strategy_status table

Revision ID: 0007_create_strategy_status
Revises: 0006_symbol_indexes_concurrently
Create Date: 2025-10-09 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_create_strategy_status'
down_revision = '0006_symbol_indexes_concurrently'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'strategy_status',
        sa.Column('strategy_id', sa.String(), primary_key=True),
        sa.Column('last_seen_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_trade_ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('open_position', sa.JSON(), nullable=True),
        sa.Column('pnl_realized', sa.Float(), nullable=True),
        sa.Column('pnl_unrealized', sa.Float(), nullable=True),
    )


def downgrade():
    op.drop_table('strategy_status')
