"""add suggestion delivery tracking

Revision ID: 45968f0ccb0e
Revises: 50b7106adecd
Create Date: 2026-08-18 14:38:57.322892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import awe.persistence.types


# revision identifiers, used by Alembic.
revision: str = '45968f0ccb0e'
down_revision: Union[str, Sequence[str], None] = '50b7106adecd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('suggestions', sa.Column('delivered_at', awe.persistence.types.UTCDateTime(timezone=True), nullable=True))
    op.add_column('suggestions', sa.Column('delivery_error', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('suggestions', 'delivery_error')
    op.drop_column('suggestions', 'delivered_at')
