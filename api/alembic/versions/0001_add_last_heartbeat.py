"""add last_heartbeat to strategies

Revision ID: 0001_add_last_heartbeat
Revises: 
Create Date: 2025-10-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_last_heartbeat'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # add nullable timestamp column
    op.add_column('strategies', sa.Column('last_heartbeat', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('strategies', 'last_heartbeat')
