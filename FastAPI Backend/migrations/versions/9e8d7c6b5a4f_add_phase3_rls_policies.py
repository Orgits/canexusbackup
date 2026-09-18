"""add_phase3_rls_policies

Revision ID: 9e8d7c6b5a4f
Revises: 8f7c3b2a1e9d
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9e8d7c6b5a4f'
down_revision: Union[str, None] = '8f7c3b2a1e9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_rls_policies(table_name: str) -> None:
    """Create RLS policies for a tenant table."""
    # Enable RLS
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    
    # Create policies using NULLIF for fail-closed behavior
    tenant_setting = "NULLIF(current_setting('app.current_tenant', true), '')::uuid"
    
    # SELECT policy
    op.execute(f"""
        CREATE POLICY {table_name}_select_policy ON {table_name}
        FOR SELECT USING (tenant_id = {tenant_setting})
    """)
    
    # INSERT policy
    op.execute(f"""
        CREATE POLICY {table_name}_insert_policy ON {table_name}
        FOR INSERT WITH CHECK (tenant_id = {tenant_setting})
    """)
    
    # UPDATE policy
    op.execute(f"""
        CREATE POLICY {table_name}_update_policy ON {table_name}
        FOR UPDATE USING (tenant_id = {tenant_setting})
        WITH CHECK (tenant_id = {tenant_setting})
    """)
    
    # DELETE policy
    op.execute(f"""
        CREATE POLICY {table_name}_delete_policy ON {table_name}
        FOR DELETE USING (tenant_id = {tenant_setting})
    """)


def upgrade() -> None:
    phase3_tables = [
        'campaigns',
        'campaign_recipients',
        'conversations',
        'conversation_messages',
        'templates',
        'consents',
        'consent_templates',
        'suppressions',
        'document_requests',
        'document_request_documents',
        'channel_providers',
        'message_logs',
        'webhook_endpoints',
        'webhook_events',
    ]
    
    for table in phase3_tables:
        _create_rls_policies(table)


def downgrade() -> None:
    phase3_tables = [
        'campaigns',
        'campaign_recipients',
        'conversations',
        'conversation_messages',
        'templates',
        'consents',
        'consent_templates',
        'suppressions',
        'document_requests',
        'document_request_documents',
        'channel_providers',
        'message_logs',
        'webhook_endpoints',
        'webhook_events',
    ]
    
    for table in phase3_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")