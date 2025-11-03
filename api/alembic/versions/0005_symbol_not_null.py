"""set symbol NOT NULL on trades and positions (safe guard)

Revision ID: 0005_symbol_not_null
Revises: 0004_add_symbol_column
Create Date: 2025-10-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '0005_symbol_not_null'
down_revision = '0004_add_symbol_column'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Safety check: abort if any NULLs remain
    trades_null = conn.execute(text("SELECT COUNT(*) FROM trades WHERE symbol IS NULL")).scalar()
    positions_null = conn.execute(text("SELECT COUNT(*) FROM positions WHERE symbol IS NULL")).scalar()
    if trades_null or positions_null:
        raise RuntimeError(f"Cannot set NOT NULL: trades.null={trades_null}, positions.null={positions_null}")

    # Now safe to alter column
    op.alter_column('trades', 'symbol', existing_type=sa.String(), nullable=False)
    op.alter_column('positions', 'symbol', existing_type=sa.String(), nullable=False)


def downgrade():
    op.alter_column('positions', 'symbol', existing_type=sa.String(), nullable=True)
    op.alter_column('trades', 'symbol', existing_type=sa.String(), nullable=True)
