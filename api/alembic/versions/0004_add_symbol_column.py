"""add symbol column to trades and positions (chunked backfill)

Revision ID: 0004_add_symbol_column
Revises: 0003_copy_execution_fields
Create Date: 2025-10-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import logging

# revision identifiers, used by Alembic.
revision = '0004_add_symbol_column'
down_revision = '0003_copy_execution_fields'
branch_labels = None
depends_on = None

LOG = logging.getLogger("alembic.0004")


def _chunked_backfill(conn, table, batch_size=10000):
    """Backfill `symbol` for a table in batches using primary key ranges.

    This function selects the lowest id with NULL symbol and updates
    rows in `[id, id+batch_size)` ranges until no NULLs remain.
    """
    while True:
        row = conn.execute(text(f"SELECT id FROM {table} WHERE symbol IS NULL AND market IS NOT NULL ORDER BY id LIMIT 1")).fetchone()
        if not row:
            LOG.info("no more null symbols for %s", table)
            break
        start = int(row[0])
        end = start + batch_size - 1
        upd = conn.execute(text(
            f"UPDATE {table} SET symbol = UPPER(market) WHERE id BETWEEN :start AND :end AND symbol IS NULL AND market IS NOT NULL"
        ), {"start": start, "end": end})
        LOG.info("updated %s rows in %s (id %s..%s)", upd.rowcount, table, start, end)
        # if nothing was updated (race or sparse ids), advance the window
        if upd.rowcount == 0:
            # try to advance beyond end; pick next candidate > end
            nxt = conn.execute(text(f"SELECT id FROM {table} WHERE symbol IS NULL AND market IS NOT NULL AND id > :end ORDER BY id LIMIT 1"), {"end": end}).fetchone()
            if not nxt:
                LOG.info("no further nulls after id %s for %s", end, table)
                break
            # otherwise loop will pick up the next start


def upgrade():
    # add symbol column (nullable for safe backfill)
    op.add_column('trades', sa.Column('symbol', sa.String(), nullable=True))
    op.add_column('positions', sa.Column('symbol', sa.String(), nullable=True))

    # Create indexes (non-concurrent by default). For very large tables
    # consider creating indexes CONCURRENTLY outside of a transaction.
    op.create_index('idx_trades_symbol', 'trades', ['symbol'])
    op.create_index('idx_positions_symbol', 'positions', ['symbol'])

    conn = op.get_bind()
    # configurable batch size; default 10k
    batch_size = 10000

    LOG.info("starting chunked backfill for trades with batch_size=%s", batch_size)
    _chunked_backfill(conn, 'trades', batch_size=batch_size)

    LOG.info("starting chunked backfill for positions with batch_size=%s", batch_size)
    _chunked_backfill(conn, 'positions', batch_size=batch_size)


def downgrade():
    op.drop_index('idx_positions_symbol', 'positions')
    op.drop_index('idx_trades_symbol', 'trades')
    op.drop_column('positions', 'symbol')
    op.drop_column('trades', 'symbol')
