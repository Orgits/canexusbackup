"""add_phase4_rls_policies

Revision ID: cb8d2c08f8bf
Revises: 324de1273e3c
Create Date: 2026-09-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'cb8d2c08f8bf'
down_revision: Union[str, None] = '324de1273e3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create RLS policies for Phase 4 tables
    tables = [
        # DSC tables
        'dsc_certificates',
        'dsc_signing_logs',
        'dsc_renewal_requests',
        # UDIN tables
        'udin_records',
        'udin_verification_logs',
        # Licenses tables
        'licenses',
        'license_documents',
        'license_renewal_requests',
        # Engagement Documents tables
        'engagement_documents',
        'engagement_document_signers',
        'engagement_document_versions',
        'engagement_document_templates',
        # E-Signature tables
        'e_signature_requests',
        'e_signers',
        'e_signature_provider_configs',
        'e_signature_webhook_events',
        # MFA tables
        'mfa_enrollments',
        'mfa_login_challenges',
        'mfa_verification_logs',
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
        # DSC tables
        'dsc_certificates',
        'dsc_signing_logs',
        'dsc_renewal_requests',
        # UDIN tables
        'udin_records',
        'udin_verification_logs',
        # Licenses tables
        'licenses',
        'license_documents',
        'license_renewal_requests',
        # Engagement Documents tables
        'engagement_documents',
        'engagement_document_signers',
        'engagement_document_versions',
        'engagement_document_templates',
        # E-Signature tables
        'e_signature_requests',
        'e_signers',
        'e_signature_provider_configs',
        'e_signature_webhook_events',
        # MFA tables
        'mfa_enrollments',
        'mfa_login_challenges',
        'mfa_verification_logs',
    ]
    
    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_policy ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_delete_policy ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")