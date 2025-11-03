"""add copy_subscribers and copy_executions tables

Revision ID: 0002_add_copy_tables
Revises: 0001_add_last_heartbeat
Create Date: 2025-10-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_copy_tables'
down_revision = '0001_add_last_heartbeat'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'copy_subscribers',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('risk_multiplier', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('max_leverage', sa.Float(), nullable=True, server_default='1.0'),
        sa.Column('enabled', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('notes', sa.String(), nullable=True),
    )

    op.create_table(
        'copy_executions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('subscriber_id', sa.Integer(), nullable=True),
        sa.Column('signal_trade_id', sa.Integer(), nullable=True),
        sa.Column('side', sa.String(), nullable=True),
        sa.Column('qty', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(), nullable=True, server_default='pending'),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table('copy_executions')
    op.drop_table('copy_subscribers')
