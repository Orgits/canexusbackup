"""add_outbox_table_v2

Revision ID: fd590f5fb5fa
Revises: daf8d97fb963
Create Date: 2026-09-16 09:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'fd590f5fb5fa'
down_revision: Union[str, None] = 'daf8d97fb963'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """This migration is a no-op since the first migration (daf8d97fb963) already created the outbox_events table with all required indexes."""
    # The first migration (daf8d97fb963) already created the outbox_events table with all required indexes.
    # This migration is a no-op since everything was already created by the first migration.
    pass


def downgrade() -> None:
    # No-op since upgrade is a no-op
    pass