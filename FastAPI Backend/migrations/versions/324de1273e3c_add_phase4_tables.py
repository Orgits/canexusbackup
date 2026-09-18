"""add_phase4_tables

Revision ID: 324de1273e3c
Revises: 8e9f7c6b5a4f
Create Date: 2026-09-19 01:20:33.990323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '324de1273e3c'
down_revision: Union[str, None] = '8e9f7c6b5a4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === Create tables in dependency order ===

    # 1. DSC tables (no internal dependencies)
    op.create_table('dsc_certificates',
    sa.Column('holder_id', sa.UUID(), nullable=False),
    sa.Column('dsc_type', sa.Enum('CLASS_1', 'CLASS_2', 'CLASS_3', 'DGFT', name='dsctype'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'REVOKED', 'PENDING_RENEWAL', 'RENEWED', name='dscstatus'), nullable=False),
    sa.Column('certificate_serial_number', sa.String(length=200), nullable=False),
    sa.Column('issuing_authority', sa.String(length=200), nullable=False),
    sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('custodian_id', sa.UUID(), nullable=True),
    sa.Column('client_id', sa.UUID(), nullable=True),
    sa.Column('certificate_pem', sa.LargeBinary(), nullable=True),
    sa.Column('private_key_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('passphrase_hash', sa.String(length=500), nullable=True),
    sa.Column('key_algorithm', sa.String(length=50), nullable=False),
    sa.Column('key_size', sa.Integer(), nullable=False),
    sa.Column('pin_hash', sa.String(length=500), nullable=True),
    sa.Column('token_serial_number', sa.String(length=100), nullable=True),
    sa.Column('token_type', sa.String(length=50), nullable=True),
    sa.Column('renewal_reminder_sent', sa.Boolean(), nullable=False),
    sa.Column('renewal_initiated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by', sa.UUID(), nullable=True),
    sa.Column('revocation_reason', sa.Text(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['custodian_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['holder_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('certificate_serial_number')
    )
    op.create_index(op.f('ix_dsc_certificates_client_id'), 'dsc_certificates', ['client_id'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_custodian_id'), 'dsc_certificates', ['custodian_id'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_dsc_type'), 'dsc_certificates', ['dsc_type'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_expiry_date'), 'dsc_certificates', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_holder_id'), 'dsc_certificates', ['holder_id'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_status'), 'dsc_certificates', ['status'], unique=False)
    op.create_index('ix_dsc_certificates_tenant_expiry', 'dsc_certificates', ['tenant_id', 'expiry_date'], unique=False)
    op.create_index('ix_dsc_certificates_tenant_holder', 'dsc_certificates', ['tenant_id', 'holder_id'], unique=False)
    op.create_index(op.f('ix_dsc_certificates_tenant_id'), 'dsc_certificates', ['tenant_id'], unique=False)
    op.create_index('ix_dsc_certificates_tenant_status', 'dsc_certificates', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_dsc_certificates_tenant_type', 'dsc_certificates', ['tenant_id', 'dsc_type'], unique=False)

    op.create_table('dsc_renewal_requests',
    sa.Column('certificate_id', sa.UUID(), nullable=False),
    sa.Column('requested_by_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('new_expiry_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('renewal_authority', sa.String(length=200), nullable=True),
    sa.Column('renewal_reference', sa.String(length=200), nullable=True),
    sa.Column('approved_by_id', sa.UUID(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_by_id', sa.UUID(), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['certificate_id'], ['dsc_certificates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rejected_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dsc_renewal_requests_approved_by_id'), 'dsc_renewal_requests', ['approved_by_id'], unique=False)
    op.create_index(op.f('ix_dsc_renewal_requests_certificate_id'), 'dsc_renewal_requests', ['certificate_id'], unique=False)
    op.create_index(op.f('ix_dsc_renewal_requests_rejected_by_id'), 'dsc_renewal_requests', ['rejected_by_id'], unique=False)
    op.create_index(op.f('ix_dsc_renewal_requests_requested_by_id'), 'dsc_renewal_requests', ['requested_by_id'], unique=False)
    op.create_index(op.f('ix_dsc_renewal_requests_status'), 'dsc_renewal_requests', ['status'], unique=False)
    op.create_index('ix_dsc_renewal_requests_tenant_certificate', 'dsc_renewal_requests', ['tenant_id', 'certificate_id'], unique=False)
    op.create_index(op.f('ix_dsc_renewal_requests_tenant_id'), 'dsc_renewal_requests', ['tenant_id'], unique=False)
    op.create_index('ix_dsc_renewal_requests_tenant_requested_by', 'dsc_renewal_requests', ['tenant_id', 'requested_by_id'], unique=False)
    op.create_index('ix_dsc_renewal_requests_tenant_status', 'dsc_renewal_requests', ['tenant_id', 'status'], unique=False)

    op.create_table('dsc_signing_logs',
    sa.Column('certificate_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('signed_by_id', sa.UUID(), nullable=False),
    sa.Column('signing_purpose', sa.String(length=200), nullable=False),
    sa.Column('signature_algorithm', sa.String(length=100), nullable=False),
    sa.Column('signature_hash', sa.String(length=200), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('request_id', sa.String(length=100), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['certificate_id'], ['dsc_certificates.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['signed_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dsc_signing_logs_certificate_id'), 'dsc_signing_logs', ['certificate_id'], unique=False)
    op.create_index(op.f('ix_dsc_signing_logs_document_id'), 'dsc_signing_logs', ['document_id'], unique=False)
    op.create_index(op.f('ix_dsc_signing_logs_signed_by_id'), 'dsc_signing_logs', ['signed_by_id'], unique=False)
    op.create_index(op.f('ix_dsc_signing_logs_status'), 'dsc_signing_logs', ['status'], unique=False)
    op.create_index('ix_dsc_signing_logs_tenant_certificate', 'dsc_signing_logs', ['tenant_id', 'certificate_id'], unique=False)
    op.create_index('ix_dsc_signing_logs_tenant_created', 'dsc_signing_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_dsc_signing_logs_tenant_document', 'dsc_signing_logs', ['tenant_id', 'document_id'], unique=False)
    op.create_index(op.f('ix_dsc_signing_logs_tenant_id'), 'dsc_signing_logs', ['tenant_id'], unique=False)
    op.create_index('ix_dsc_signing_logs_tenant_status', 'dsc_signing_logs', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_dsc_signing_logs_tenant_user', 'dsc_signing_logs', ['tenant_id', 'signed_by_id'], unique=False)

    # 2. UDIN tables
    op.create_table('udin_records',
    sa.Column('udin', sa.String(length=20), nullable=False),
    sa.Column('professional_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Enum('GENERATED', 'VERIFIED', 'CANCELLED', 'EXPIRED', name='udinstatus'), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=True),
    sa.Column('matter_id', sa.UUID(), nullable=True),
    sa.Column('document_id', sa.UUID(), nullable=True),
    sa.Column('financial_year', sa.String(length=20), nullable=False),
    sa.Column('quarter', sa.String(length=10), nullable=True),
    sa.Column('form_type', sa.String(length=50), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('verified_by_id', sa.UUID(), nullable=True),
    sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cancelled_by_id', sa.UUID(), nullable=True),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('external_reference', sa.String(length=100), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['cancelled_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['matter_id'], ['matters.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['professional_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('udin')
    )
    op.create_index(op.f('ix_udin_records_client_id'), 'udin_records', ['client_id'], unique=False)
    op.create_index(op.f('ix_udin_records_document_id'), 'udin_records', ['document_id'], unique=False)
    op.create_index(op.f('ix_udin_records_financial_year'), 'udin_records', ['financial_year'], unique=False)
    op.create_index(op.f('ix_udin_records_generated_at'), 'udin_records', ['generated_at'], unique=False)
    op.create_index(op.f('ix_udin_records_matter_id'), 'udin_records', ['matter_id'], unique=False)
    op.create_index(op.f('ix_udin_records_professional_id'), 'udin_records', ['professional_id'], unique=False)
    op.create_index(op.f('ix_udin_records_status'), 'udin_records', ['status'], unique=False)
    op.create_index('ix_udin_records_tenant_client', 'udin_records', ['tenant_id', 'client_id'], unique=False)
    op.create_index('ix_udin_records_tenant_document', 'udin_records', ['tenant_id', 'document_id'], unique=False)
    op.create_index('ix_udin_records_tenant_generated', 'udin_records', ['tenant_id', 'generated_at'], unique=False)
    op.create_index(op.f('ix_udin_records_tenant_id'), 'udin_records', ['tenant_id'], unique=False)
    op.create_index('ix_udin_records_tenant_matter', 'udin_records', ['tenant_id', 'matter_id'], unique=False)
    op.create_index('ix_udin_records_tenant_professional', 'udin_records', ['tenant_id', 'professional_id'], unique=False)
    op.create_index('ix_udin_records_tenant_status', 'udin_records', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_udin_records_tenant_udin', 'udin_records', ['tenant_id', 'udin'], unique=False)
    op.create_index(op.f('ix_udin_records_udin'), 'udin_records', ['udin'], unique=False)

    op.create_table('udin_verification_logs',
    sa.Column('udin_record_id', sa.UUID(), nullable=False),
    sa.Column('verified_by_id', sa.UUID(), nullable=False),
    sa.Column('result', sa.String(length=50), nullable=False),
    sa.Column('verification_method', sa.String(length=50), nullable=False),
    sa.Column('external_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.Text(), nullable=True),
    sa.Column('request_id', sa.String(length=100), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['udin_record_id'], ['udin_records.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_udin_verification_logs_result'), 'udin_verification_logs', ['result'], unique=False)
    op.create_index('ix_udin_verification_logs_tenant_id', 'udin_verification_logs', ['tenant_id'], unique=False)
    op.create_index('ix_udin_verification_logs_tenant_result', 'udin_verification_logs', ['tenant_id', 'result'], unique=False)
    op.create_index('ix_udin_verification_logs_tenant_udin', 'udin_verification_logs', ['tenant_id', 'udin_record_id'], unique=False)
    op.create_index('ix_udin_verification_logs_tenant_user', 'udin_verification_logs', ['tenant_id', 'verified_by_id'], unique=False)
    op.create_index(op.f('ix_udin_verification_logs_udin_record_id'), 'udin_verification_logs', ['udin_record_id'], unique=False)
    op.create_index(op.f('ix_udin_verification_logs_verified_by_id'), 'udin_verification_logs', ['verified_by_id'], unique=False)

    # 3. Licenses tables
    op.create_table('licenses',
    sa.Column('professional_id', sa.UUID(), nullable=False),
    sa.Column('license_type', sa.Enum('CA_CERTIFICATE', 'CA_PRACTICE_CERTIFICATE', 'GST_PRACTITIONER', 'TAX_AUDITOR', 'COMPANY_SECRETARY', 'COST_ACCOUNTANT', 'INSOLVENCY_PROFESSIONAL', 'REGISTERED_VALUER', 'PEER_REVIEW_CERTIFICATE', 'QUALITY_REVIEW_CERTIFICATE', 'FCRA_REGISTRATION', 'INCOME_TAX_PRACTITIONER', 'OTHER', name='licensetype'), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'EXPIRED', 'PENDING_RENEWAL', 'RENEWED', 'SUSPENDED', 'REVOKED', 'SURRENDERED', name='licensestatus'), nullable=False),
    sa.Column('license_number', sa.String(length=100), nullable=False),
    sa.Column('issuing_authority', sa.String(length=200), nullable=False),
    sa.Column('issue_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('registration_number', sa.String(length=100), nullable=True),
    sa.Column('jurisdiction', sa.String(length=100), nullable=True),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('conditions', sa.Text(), nullable=True),
    sa.Column('renewal_application_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('renewal_acknowledgment_number', sa.String(length=100), nullable=True),
    sa.Column('renewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('renewed_by_id', sa.UUID(), nullable=True),
    sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('suspended_by_id', sa.UUID(), nullable=True),
    sa.Column('suspension_reason', sa.Text(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by_id', sa.UUID(), nullable=True),
    sa.Column('revocation_reason', sa.Text(), nullable=True),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['professional_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['renewed_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['revoked_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['suspended_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('license_number')
    )
    op.create_index(op.f('ix_licenses_expiry_date'), 'licenses', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_licenses_license_type'), 'licenses', ['license_type'], unique=False)
    op.create_index(op.f('ix_licenses_professional_id'), 'licenses', ['professional_id'], unique=False)
    op.create_index(op.f('ix_licenses_status'), 'licenses', ['status'], unique=False)
    op.create_index('ix_licenses_tenant_expiry', 'licenses', ['tenant_id', 'expiry_date'], unique=False)
    op.create_index(op.f('ix_licenses_tenant_id'), 'licenses', ['tenant_id'], unique=False)
    op.create_index('ix_licenses_tenant_number', 'licenses', ['tenant_id', 'license_number'], unique=False)
    op.create_index('ix_licenses_tenant_professional', 'licenses', ['tenant_id', 'professional_id'], unique=False)
    op.create_index('ix_licenses_tenant_status', 'licenses', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_licenses_tenant_type', 'licenses', ['tenant_id', 'license_type'], unique=False)

    op.create_table('license_documents',
    sa.Column('license_id', sa.UUID(), nullable=False),
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('document_type', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('uploaded_by_id', sa.UUID(), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_license_documents_document_id'), 'license_documents', ['document_id'], unique=False)
    op.create_index('ix_license_documents_tenant_document', 'license_documents', ['tenant_id', 'document_id'], unique=False)
    op.create_index(op.f('ix_license_documents_tenant_id'), 'license_documents', ['tenant_id'], unique=False)
    op.create_index('ix_license_documents_tenant_license', 'license_documents', ['tenant_id', 'license_id'], unique=False)
    op.create_index(op.f('ix_license_documents_uploaded_by_id'), 'license_documents', ['uploaded_by_id'], unique=False)

    op.create_table('license_renewal_requests',
    sa.Column('license_id', sa.UUID(), nullable=False),
    sa.Column('requested_by_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('new_expiry_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('application_number', sa.String(length=100), nullable=True),
    sa.Column('application_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('fees_paid', sa.Boolean(), nullable=False),
    sa.Column('fees_amount', sa.Float(), nullable=True),
    sa.Column('fees_paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by_id', sa.UUID(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejected_by_id', sa.UUID(), nullable=True),
    sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rejection_reason', sa.Text(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['license_id'], ['licenses.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rejected_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['requested_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_license_renewal_requests_approved_by_id'), 'license_renewal_requests', ['approved_by_id'], unique=False)
    op.create_index(op.f('ix_license_renewal_requests_license_id'), 'license_renewal_requests', ['license_id'], unique=False)
    op.create_index(op.f('ix_license_renewal_requests_rejected_by_id'), 'license_renewal_requests', ['rejected_by_id'], unique=False)
    op.create_index(op.f('ix_license_renewal_requests_requested_by_id'), 'license_renewal_requests', ['requested_by_id'], unique=False)
    op.create_index(op.f('ix_license_renewal_requests_status'), 'license_renewal_requests', ['status'], unique=False)
    op.create_index('ix_license_renewal_requests_tenant_license', 'license_renewal_requests', ['tenant_id', 'license_id'], unique=False)
    op.create_index(op.f('ix_license_renewal_requests_tenant_id'), 'license_renewal_requests', ['tenant_id'], unique=False)
    op.create_index('ix_license_renewal_requests_tenant_requested_by', 'license_renewal_requests', ['tenant_id', 'requested_by_id'], unique=False)
    op.create_index('ix_license_renewal_requests_tenant_status', 'license_renewal_requests', ['tenant_id', 'status'], unique=False)

    # 4. Engagement Document Templates (no dependencies)
    op.create_table('engagement_document_templates',
    sa.Column('document_type', sa.Enum('ENGAGEMENT_LETTER', 'REPRESENTATION_LETTER', 'MANAGEMENT_LETTER', 'CONFIRMATION_LETTER', 'INDEPENDENCE_DECLARATION', 'TERMS_OF_BUSINESS', 'SCOPE_OF_WORK', 'FEE_AGREEMENT', 'NDA', 'OTHER', name='engagementdocumenttype'), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('content_template', sa.Text(), nullable=False),
    sa.Column('html_template', sa.Text(), nullable=True),
    sa.Column('default_variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('required_variables', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagement_document_templates_created_by_id'), 'engagement_document_templates', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_engagement_document_templates_document_type'), 'engagement_document_templates', ['document_type'], unique=False)
    op.create_index('ix_engagement_document_templates_tenant_active', 'engagement_document_templates', ['tenant_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_engagement_document_templates_tenant_id'), 'engagement_document_templates', ['tenant_id'], unique=False)
    op.create_index('ix_engagement_document_templates_tenant_type', 'engagement_document_templates', ['tenant_id', 'document_type'], unique=False)

    # 5. E-Signature Provider Configs (no dependencies)
    op.create_table('e_signature_provider_configs',
    sa.Column('provider', sa.Enum('DOCUSIGN', 'ADOBE_SIGN', 'HELLOSIGN', 'PANDA_DOC', 'SIGNNOW', 'INTERNAL', name='esignatureprovider'), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_default', sa.Boolean(), nullable=False),
    sa.Column('api_base_url', sa.String(length=500), nullable=False),
    sa.Column('client_id', sa.String(length=200), nullable=False),
    sa.Column('client_secret_encrypted', sa.LargeBinary(), nullable=False),
    sa.Column('account_id', sa.String(length=200), nullable=True),
    sa.Column('webhook_secret_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('oauth_redirect_uri', sa.String(length=500), nullable=True),
    sa.Column('scopes', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False),
    sa.Column('timeout_seconds', sa.Integer(), nullable=False),
    sa.Column('extra_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_e_signature_provider_configs_provider'), 'e_signature_provider_configs', ['provider'], unique=False)
    op.create_index(op.f('ix_e_signature_provider_configs_tenant_id'), 'e_signature_provider_configs', ['tenant_id'], unique=False)
    op.create_index('ix_e_signature_provider_configs_tenant_provider', 'e_signature_provider_configs', ['tenant_id', 'provider'], unique=False)

    # 6. MFA tables
    op.create_table('mfa_enrollments',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('method', sa.Enum('TOTP', 'SMS', 'EMAIL', 'BACKUP_CODES', name='mfamethod'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'DISABLED', 'LOCKED', name='mfaenrollmentstatus'), nullable=False),
    sa.Column('totp_secret_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('totp_algorithm', sa.String(length=20), nullable=False),
    sa.Column('totp_digits', sa.Integer(), nullable=False),
    sa.Column('totp_period', sa.Integer(), nullable=False),
    sa.Column('totp_issuer', sa.String(length=100), nullable=False),
    sa.Column('backup_codes_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('backup_codes_used', sa.ARRAY(sa.String()), nullable=False),
    sa.Column('phone_number', sa.String(length=50), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('disabled_by_id', sa.UUID(), nullable=True),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lock_reason', sa.String(length=200), nullable=True),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('last_failed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['disabled_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mfa_enrollments_method'), 'mfa_enrollments', ['method'], unique=False)
    op.create_index(op.f('ix_mfa_enrollments_status'), 'mfa_enrollments', ['status'], unique=False)
    op.create_index(op.f('ix_mfa_enrollments_tenant_id'), 'mfa_enrollments', ['tenant_id'], unique=False)
    op.create_index('ix_mfa_enrollments_tenant_status', 'mfa_enrollments', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_mfa_enrollments_tenant_user', 'mfa_enrollments', ['tenant_id', 'user_id'], unique=False)
    op.create_index(op.f('ix_mfa_enrollments_user_id'), 'mfa_enrollments', ['user_id'], unique=False)

    op.create_table('mfa_login_challenges',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('challenge_id', sa.String(length=100), nullable=False),
    sa.Column('method', sa.Enum('TOTP', 'SMS', 'EMAIL', 'BACKUP_CODES', name='mfamethod'), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('totp_code_hash', sa.String(length=200), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('session_id', sa.String(length=100), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('challenge_id')
    )
    op.create_index(op.f('ix_mfa_login_challenges_status'), 'mfa_login_challenges', ['status'], unique=False)
    op.create_index('ix_mfa_login_challenges_tenant_challenge', 'mfa_login_challenges', ['tenant_id', 'challenge_id'], unique=False)
    op.create_index('ix_mfa_login_challenges_tenant_expires', 'mfa_login_challenges', ['tenant_id', 'expires_at'], unique=False)
    op.create_index(op.f('ix_mfa_login_challenges_tenant_id'), 'mfa_login_challenges', ['tenant_id'], unique=False)
    op.create_index('ix_mfa_login_challenges_tenant_status', 'mfa_login_challenges', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_mfa_login_challenges_tenant_user', 'mfa_login_challenges', ['tenant_id', 'user_id'], unique=False)
    op.create_index(op.f('ix_mfa_login_challenges_user_id'), 'mfa_login_challenges', ['user_id'], unique=False)

    op.create_table('mfa_verification_logs',
    sa.Column('enrollment_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('method', sa.Enum('TOTP', 'SMS', 'EMAIL', 'BACKUP_CODES', name='mfamethod'), nullable=False),
    sa.Column('result', sa.String(length=50), nullable=False),
    sa.Column('ip_address', sa.String(length=50), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('challenge_id', sa.String(length=100), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['enrollment_id'], ['mfa_enrollments.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mfa_verification_logs_enrollment_id'), 'mfa_verification_logs', ['enrollment_id'], unique=False)
    op.create_index(op.f('ix_mfa_verification_logs_result'), 'mfa_verification_logs', ['result'], unique=False)
    op.create_index('ix_mfa_verification_logs_tenant_created', 'mfa_verification_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_mfa_verification_logs_tenant_enrollment', 'mfa_verification_logs', ['tenant_id', 'enrollment_id'], unique=False)
    op.create_index(op.f('ix_mfa_verification_logs_tenant_id'), 'mfa_verification_logs', ['tenant_id'], unique=False)
    op.create_index('ix_mfa_verification_logs_tenant_result', 'mfa_verification_logs', ['tenant_id', 'result'], unique=False)
    op.create_index('ix_mfa_verification_logs_tenant_user', 'mfa_verification_logs', ['tenant_id', 'user_id'], unique=False)
    op.create_index(op.f('ix_mfa_verification_logs_user_id'), 'mfa_verification_logs', ['user_id'], unique=False)

    # 7. Create engagement_documents WITH e_signature_request_id column (no FK yet)
    op.create_table('engagement_documents',
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('matter_id', sa.UUID(), nullable=True),
    sa.Column('document_type', sa.Enum('ENGAGEMENT_LETTER', 'REPRESENTATION_LETTER', 'MANAGEMENT_LETTER', 'CONFIRMATION_LETTER', 'INDEPENDENCE_DECLARATION', 'TERMS_OF_BUSINESS', 'SCOPE_OF_WORK', 'FEE_AGREEMENT', 'NDA', 'OTHER', name='engagementdocumenttype'), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'PENDING_REVIEW', 'PENDING_SIGNATURE', 'PARTIALLY_SIGNED', 'FULLY_SIGNED', 'COMPLETED', 'EXPIRED', 'CANCELLED', name='engagementdocumentstatus'), nullable=False),
    sa.Column('document_number', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('template_id', sa.UUID(), nullable=True),
    sa.Column('template_version', sa.Integer(), nullable=True),
    sa.Column('document_content', sa.Text(), nullable=True),
    sa.Column('document_html', sa.Text(), nullable=True),
    sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('engagement_partner_id', sa.UUID(), nullable=True),
    sa.Column('engagement_manager_id', sa.UUID(), nullable=True),
    sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
    sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
    sa.Column('fee_estimate', sa.Float(), nullable=True),
    sa.Column('fee_terms', sa.Text(), nullable=True),
    sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
    sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('e_signature_request_id', sa.UUID(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['engagement_manager_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['engagement_partner_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['matter_id'], ['matters.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_number')
    )
    op.create_index(op.f('ix_engagement_documents_client_id'), 'engagement_documents', ['client_id'], unique=False)
    op.create_index(op.f('ix_engagement_documents_document_type'), 'engagement_documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_engagement_documents_engagement_manager_id'), 'engagement_documents', ['engagement_manager_id'], unique=False)
    op.create_index(op.f('ix_engagement_documents_engagement_partner_id'), 'engagement_documents', ['engagement_partner_id'], unique=False)
    op.create_index(op.f('ix_engagement_documents_matter_id'), 'engagement_documents', ['matter_id'], unique=False)
    op.create_index(op.f('ix_engagement_documents_status'), 'engagement_documents', ['status'], unique=False)
    op.create_index('ix_engagement_documents_tenant_client', 'engagement_documents', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_engagement_documents_tenant_id'), 'engagement_documents', ['tenant_id'], unique=False)
    op.create_index('ix_engagement_documents_tenant_matter', 'engagement_documents', ['tenant_id', 'matter_id'], unique=False)
    op.create_index('ix_engagement_documents_tenant_number', 'engagement_documents', ['tenant_id', 'document_number'], unique=False)
    op.create_index('ix_engagement_documents_tenant_status', 'engagement_documents', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_engagement_documents_tenant_type', 'engagement_documents', ['tenant_id', 'document_type'], unique=False)

    op.create_table('engagement_document_signers',
    sa.Column('engagement_document_id', sa.UUID(), nullable=False),
    sa.Column('signer_id', sa.UUID(), nullable=False),
    sa.Column('signer_role', sa.String(length=100), nullable=False),
    sa.Column('signing_order', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signature_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decline_reason', sa.Text(), nullable=True),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reminder_count', sa.Integer(), nullable=False),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['engagement_document_id'], ['engagement_documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['signer_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagement_document_signers_engagement_document_id'), 'engagement_document_signers', ['engagement_document_id'], unique=False)
    op.create_index(op.f('ix_engagement_document_signers_signer_id'), 'engagement_document_signers', ['signer_id'], unique=False)
    op.create_index(op.f('ix_engagement_document_signers_status'), 'engagement_document_signers', ['status'], unique=False)
    op.create_index('ix_engagement_document_signers_tenant_document', 'engagement_document_signers', ['tenant_id', 'engagement_document_id'], unique=False)
    op.create_index(op.f('ix_engagement_document_signers_tenant_id'), 'engagement_document_signers', ['tenant_id'], unique=False)
    op.create_index('ix_engagement_document_signers_tenant_status', 'engagement_document_signers', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_engagement_document_signers_tenant_user', 'engagement_document_signers', ['tenant_id', 'signer_id'], unique=False)

    op.create_table('engagement_document_versions',
    sa.Column('engagement_document_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('document_content', sa.Text(), nullable=True),
    sa.Column('document_html', sa.Text(), nullable=True),
    sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_by_id', sa.UUID(), nullable=False),
    sa.Column('change_summary', sa.Text(), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['engagement_document_id'], ['engagement_documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_engagement_document_versions_created_by_id'), 'engagement_document_versions', ['created_by_id'], unique=False)
    op.create_index('ix_engagement_document_versions_tenant_document', 'engagement_document_versions', ['tenant_id', 'engagement_document_id'], unique=False)
    op.create_index(op.f('ix_engagement_document_versions_tenant_id'), 'engagement_document_versions', ['tenant_id'], unique=False)

    # 8. E-Signature tables
    op.create_table('e_signature_requests',
    sa.Column('document_id', sa.UUID(), nullable=False),
    sa.Column('engagement_document_id', sa.UUID(), nullable=True),
    sa.Column('provider', sa.Enum('DOCUSIGN', 'ADOBE_SIGN', 'HELLOSIGN', 'PANDA_DOC', 'SIGNNOW', 'INTERNAL', name='esignatureprovider'), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'PENDING', 'SENT', 'IN_PROGRESS', 'COMPLETED', 'DECLINED', 'EXPIRED', 'CANCELLED', 'FAILED', name='esignaturerequeststatus'), nullable=False),
    sa.Column('external_request_id', sa.String(length=200), nullable=True),
    sa.Column('title', sa.String(length=500), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('signing_order', sa.Boolean(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reminder_frequency_days', sa.Integer(), nullable=True),
    sa.Column('reminder_count', sa.Integer(), nullable=False),
    sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('declined_by_id', sa.UUID(), nullable=True),
    sa.Column('decline_reason', sa.Text(), nullable=True),
    sa.Column('provider_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('webhook_events', sa.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=False),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['declined_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['engagement_document_id'], ['engagement_documents.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('external_request_id')
    )
    op.create_index(op.f('ix_e_signature_requests_document_id'), 'e_signature_requests', ['document_id'], unique=False)
    op.create_index(op.f('ix_e_signature_requests_provider'), 'e_signature_requests', ['provider'], unique=False)
    op.create_index(op.f('ix_e_signature_requests_status'), 'e_signature_requests', ['status'], unique=False)
    op.create_index('ix_e_signature_requests_tenant_created', 'e_signature_requests', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_e_signature_requests_tenant_document', 'e_signature_requests', ['tenant_id', 'document_id'], unique=False)
    op.create_index('ix_e_signature_requests_tenant_external_id', 'e_signature_requests', ['tenant_id', 'external_request_id'], unique=False)
    op.create_index(op.f('ix_e_signature_requests_tenant_id'), 'e_signature_requests', ['tenant_id'], unique=False)
    op.create_index('ix_e_signature_requests_tenant_provider', 'e_signature_requests', ['tenant_id', 'provider'], unique=False)
    op.create_index('ix_e_signature_requests_tenant_status', 'e_signature_requests', ['tenant_id', 'status'], unique=False)

    op.create_table('e_signers',
    sa.Column('request_id', sa.UUID(), nullable=False),
    sa.Column('signer_id', sa.UUID(), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('role', sa.String(length=100), nullable=False),
    sa.Column('signing_order', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'SENT', 'VIEWED', 'SIGNED', 'DECLINED', 'EXPIRED', name='esignerstatus'), nullable=False),
    sa.Column('external_signer_id', sa.String(length=200), nullable=True),
    sa.Column('authentication_method', sa.String(length=50), nullable=True),
    sa.Column('access_code', sa.String(length=100), nullable=True),
    sa.Column('phone_number', sa.String(length=50), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('signed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('declined_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('decline_reason', sa.Text(), nullable=True),
    sa.Column('signature_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('provider_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['request_id'], ['e_signature_requests.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['signer_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_e_signers_email'), 'e_signers', ['email'], unique=False)
    op.create_index(op.f('ix_e_signers_request_id'), 'e_signers', ['request_id'], unique=False)
    op.create_index(op.f('ix_e_signers_signer_id'), 'e_signers', ['signer_id'], unique=False)
    op.create_index(op.f('ix_e_signers_status'), 'e_signers', ['status'], unique=False)
    op.create_index('ix_e_signers_tenant_email', 'e_signers', ['tenant_id', 'email'], unique=False)
    op.create_index('ix_e_signers_tenant_external_id', 'e_signers', ['tenant_id', 'external_signer_id'], unique=False)
    op.create_index(op.f('ix_e_signers_tenant_id'), 'e_signers', ['tenant_id'], unique=False)
    op.create_index('ix_e_signers_tenant_request', 'e_signers', ['tenant_id', 'request_id'], unique=False)
    op.create_index('ix_e_signers_tenant_status', 'e_signers', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_e_signers_tenant_user', 'e_signers', ['tenant_id', 'signer_id'], unique=False)

    op.create_table('e_signature_webhook_events',
    sa.Column('provider', sa.Enum('DOCUSIGN', 'ADOBE_SIGN', 'HELLOSIGN', 'PANDA_DOC', 'SIGNNOW', 'INTERNAL', name='esignatureprovider'), nullable=False),
    sa.Column('external_event_id', sa.String(length=200), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('external_request_id', sa.String(length=200), nullable=True),
    sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('processed', sa.Boolean(), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('processing_error', sa.Text(), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=200), nullable=True),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_e_signature_webhook_events_provider'), 'e_signature_webhook_events', ['provider'], unique=False)
    op.create_index(op.f('ix_e_signature_webhook_events_received_at'), 'e_signature_webhook_events', ['received_at'], unique=False)
    op.create_index('ix_e_signature_webhook_events_tenant_external_id', 'e_signature_webhook_events', ['tenant_id', 'external_event_id'], unique=False)
    op.create_index(op.f('ix_e_signature_webhook_events_tenant_id'), 'e_signature_webhook_events', ['tenant_id'], unique=False)
    op.create_index('ix_e_signature_webhook_events_tenant_processed', 'e_signature_webhook_events', ['tenant_id', 'processed'], unique=False)
    op.create_index('ix_e_signature_webhook_events_tenant_provider', 'e_signature_webhook_events', ['tenant_id', 'provider'], unique=False)
    op.create_index('ix_e_signature_webhook_events_tenant_received', 'e_signature_webhook_events', ['tenant_id', 'received_at'], unique=False)


def downgrade() -> None:
    op.drop_table('e_signature_webhook_events')
    op.drop_table('e_signers')
    op.drop_table('e_signature_requests')
    op.drop_table('engagement_document_versions')
    op.drop_table('engagement_document_signers')
    op.drop_table('engagement_documents')
    op.drop_table('engagement_document_templates')
    op.drop_table('license_renewal_requests')
    op.drop_table('license_documents')
    op.drop_table('licenses')
    op.drop_table('udin_verification_logs')
    op.drop_table('udin_records')
    op.drop_table('mfa_verification_logs')
    op.drop_table('mfa_login_challenges')
    op.drop_table('mfa_enrollments')
    op.drop_table('e_signature_webhook_events')
    op.drop_table('e_signature_provider_configs')
    op.drop_table('dsc_signing_logs')
    op.drop_table('dsc_renewal_requests')
    op.drop_table('dsc_certificates')