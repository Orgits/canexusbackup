"""add_campaign_fk_to_communications

Revision ID: 8f7c3b2a1e9d
Revises: 7a3b9c1f2e4d
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f7c3b2a1e9d'
down_revision: Union[str, None] = '7a3b9c1f2e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add foreign key from communications.campaign_id to campaigns.id
    op.create_foreign_key(
        'fk_communications_campaign_id',
        'communications', 'campaigns',
        ['campaign_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_communications_campaign_id', 'communications', type_='foreignkey')