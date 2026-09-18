"""add_audit_workspace_rls

Revision ID: 8e9f7c6b5a4f
Revises: 0be7213a0577
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8e9f7c6b5a4f'
down_revision: Union[str, None] = '0be7213a0577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create RLS policies for audit_workspace tables
    tables = [
        'audit_engagements',
        'audit_working_papers',
        'audit_evidence',
        'audit_reviews',
        'audit_sign_offs',
    ]
    
    for table in tables:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        
        tenant_setting = "NULLIF(current_setting('app.current_tenant', true), '')::uuid"
        
        op.execute(f"""
            CREATE POLICY {table}_select_policy ON {table}
            FOR SELECT USING (tenant_id = {tenant_setting})
        """)
        op.execute(f"""
            CREATE POLICY {table}_insert_policy ON {table}
            FOR INSERT WITH CHECK (tenant_id = {tenant_setting})
        """)
        op.execute(f"""
            CREATE POLICY {table}_update_policy ON {table}
            FOR UPDATE USING (tenant_id = {tenant_setting})
            WITH CHECK (tenant_id = {tenant_setting})
        """)
        op.execute(f"""
            CREATE POLICY {table}_delete_policy ON {table}
            FOR DELETE USING (tenant_id = {tenant_setting})
        """)


def downgrade() -> None:
    tables = [
        'audit_engagements',
        'audit_working_papers',
        'audit_evidence',
        'audit_reviews',
        'audit_sign_offs',
    ]
    
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")