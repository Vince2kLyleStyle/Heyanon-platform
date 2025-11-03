"""create symbol indexes concurrently (zero-downtime)

Revision ID: 0006_symbol_indexes_concurrently
Revises: 0005_symbol_not_null
Create Date: 2025-10-08 00:00:00.000000
"""
from alembic import op
from alembic.runtime.migration import MigrationContext

# revision identifiers, used by Alembic.
revision = '0006_symbol_indexes_concurrently'
down_revision = '0005_symbol_not_null'
branch_labels = None
depends_on = None


def upgrade():
    ctx = op.get_context()
    if not isinstance(ctx, MigrationContext):
        raise RuntimeError("Invalid Alembic context for concurrent index creation")
    # Safer zero-downtime swap: create concurrent indexes first, then drop old indexes.
    # Create concurrent indexes. IF NOT EXISTS guard is supported in Postgres 9.5+.
    with ctx.autocommit_block():
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_positions_symbol ON positions(symbol)")

    # Once concurrent indexes exist, drop any previous non-concurrent indexes.
    with ctx.autocommit_block():
        op.execute("DROP INDEX IF EXISTS idx_trades_symbol")
        op.execute("DROP INDEX IF EXISTS idx_positions_symbol")


def downgrade():
    ctx = op.get_context()
    # To rollback, recreate non-concurrent indexes (if needed) then drop concurrent ones.
    with ctx.autocommit_block():
        op.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
    with ctx.autocommit_block():
        op.execute("DROP INDEX IF EXISTS idx_trades_symbol")
        op.execute("DROP INDEX IF EXISTS idx_positions_symbol")
