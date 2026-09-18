"""add_ocr_ai_rls

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_rls_policies(table_name: str) -> None:
    """Create RLS policies for a tenant table."""
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    tenant_setting = "NULLIF(current_setting('app.current_tenant', true), '')::uuid"

    op.execute(f"""
        CREATE POLICY {table_name}_select_policy ON {table_name}
        FOR SELECT USING (tenant_id = {tenant_setting})
    """)
    op.execute(f"""
        CREATE POLICY {table_name}_insert_policy ON {table_name}
        FOR INSERT WITH CHECK (tenant_id = {tenant_setting})
    """)
    op.execute(f"""
        CREATE POLICY {table_name}_update_policy ON {table_name}
        FOR UPDATE USING (tenant_id = {tenant_setting})
        WITH CHECK (tenant_id = {tenant_setting})
    """)
    op.execute(f"""
        CREATE POLICY {table_name}_delete_policy ON {table_name}
        FOR DELETE USING (tenant_id = {tenant_setting})
    """)


def upgrade() -> None:
    tables = [
        'ocr_templates',
        'ocr_jobs',
        'ai_models',
        'ai_processing_jobs',
        'ai_confidence_thresholds',
        'ai_review_tasks',
    ]
    for table in tables:
        _create_rls_policies(table)


def downgrade() -> None:
    tables = [
        'ocr_templates',
        'ocr_jobs',
        'ai_models',
        'ai_processing_jobs',
        'ai_confidence_thresholds',
        'ai_review_tasks',
    ]
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")