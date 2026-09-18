"""Add Phase 5 tables: reporting, dpdp, retention

Revision ID: f5a1b2c3d4e5
Revises: cb8d2c08f8bf
Create Date: 2026-09-19 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f5a1b2c3d4e5'
down_revision: Union[str, None] = 'cb8d2c08f8bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Report Definitions
    op.create_table(
        'report_definitions',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('query_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('output_format', sa.Enum('PDF', 'EXCEL', 'CSV', 'JSON', name='reportformat', create_type=True), nullable=False, server_default='PDF'),
        sa.Column('output_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_definitions_tenant_category', 'report_definitions', ['tenant_id', 'category'], unique=False)
    op.create_index('ix_report_definitions_tenant_active', 'report_definitions', ['tenant_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_report_definitions_category'), 'report_definitions', ['category'], unique=False)
    op.create_index(op.f('ix_report_definitions_tenant_id'), 'report_definitions', ['tenant_id'], unique=False)

    # Report Parameters
    op.create_table(
        'report_parameters',
        sa.Column('report_definition_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('param_type', sa.String(length=50), nullable=False),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_value', sa.Text(), nullable=True),
        sa.Column('options', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('validation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['report_definition_id'], ['report_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_parameters_tenant_definition', 'report_parameters', ['tenant_id', 'report_definition_id'], unique=False)
    op.create_index(op.f('ix_report_parameters_report_definition_id'), 'report_parameters', ['report_definition_id'], unique=False)
    op.create_index(op.f('ix_report_parameters_tenant_id'), 'report_parameters', ['tenant_id'], unique=False)

    # Report Jobs
    op.create_table(
        'report_jobs',
        sa.Column('report_definition_id', sa.UUID(), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('status', sa.Enum('PENDING', 'QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', 'EXPIRED', name='reportstatus', create_type=True), nullable=False, server_default='PENDING'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('result_ref', sa.String(length=500), nullable=True),
        sa.Column('result_format', sa.Enum('PDF', 'EXCEL', 'CSV', 'JSON', name='reportformat', create_type=False), nullable=True),
        sa.Column('result_size', sa.Integer(), nullable=True),
        sa.Column('result_checksum', sa.String(length=64), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['report_definition_id'], ['report_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_jobs_tenant_definition', 'report_jobs', ['tenant_id', 'report_definition_id'], unique=False)
    op.create_index('ix_report_jobs_tenant_status', 'report_jobs', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_report_jobs_tenant_created', 'report_jobs', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_report_jobs_idempotency_key', 'report_jobs', ['tenant_id', 'idempotency_key'], unique=True)
    op.create_index(op.f('ix_report_jobs_report_definition_id'), 'report_jobs', ['report_definition_id'], unique=False)
    op.create_index(op.f('ix_report_jobs_status'), 'report_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_report_jobs_tenant_id'), 'report_jobs', ['tenant_id'], unique=False)

    # Report Outputs
    op.create_table(
        'report_outputs',
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('format', sa.Enum('PDF', 'EXCEL', 'CSV', 'JSON', name='reportformat', create_type=False), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('checksum', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['report_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_outputs_tenant_job', 'report_outputs', ['tenant_id', 'job_id'], unique=False)
    op.create_index(op.f('ix_report_outputs_job_id'), 'report_outputs', ['job_id'], unique=False)
    op.create_index(op.f('ix_report_outputs_tenant_id'), 'report_outputs', ['tenant_id'], unique=False)

    # Report Schedules
    op.create_table(
        'report_schedules',
        sa.Column('report_definition_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='UTC'),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('recipients', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_run_status', sa.String(length=50), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['report_definition_id'], ['report_definitions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_report_schedules_tenant_definition', 'report_schedules', ['tenant_id', 'report_definition_id'], unique=False)
    op.create_index('ix_report_schedules_tenant_active', 'report_schedules', ['tenant_id', 'is_active'], unique=False)
    op.create_index('ix_report_schedules_next_run', 'report_schedules', ['next_run_at'], unique=False)
    op.create_index(op.f('ix_report_schedules_report_definition_id'), 'report_schedules', ['report_definition_id'], unique=False)
    op.create_index(op.f('ix_report_schedules_tenant_id'), 'report_schedules', ['tenant_id'], unique=False)

    # Dashboard Widgets
    op.create_table(
        'dashboard_widgets',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('widget_type', sa.String(length=50), nullable=False),
        sa.Column('query_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('display_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('layout', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_dashboard_widgets_tenant_type', 'dashboard_widgets', ['tenant_id', 'widget_type'], unique=False)
    op.create_index('ix_dashboard_widgets_tenant_active', 'dashboard_widgets', ['tenant_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_dashboard_widgets_tenant_id'), 'dashboard_widgets', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_dashboard_widgets_widget_type'), 'dashboard_widgets', ['widget_type'], unique=False)

    # Data Access Requests
    op.create_table(
        'data_access_requests',
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('legal_basis', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'COMPILING', 'READY', 'DELIVERED', 'EXPIRED', 'FAILED', name='dataaccessstatus', create_type=True), nullable=False, server_default='PENDING'),
        sa.Column('compiled_data_ref', sa.String(length=500), nullable=True),
        sa.Column('compiled_size', sa.Integer(), nullable=True),
        sa.Column('compiled_checksum', sa.String(length=64), nullable=True),
        sa.Column('approved_by_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subject_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_access_requests_tenant_subject', 'data_access_requests', ['tenant_id', 'subject_id'], unique=False)
    op.create_index('ix_data_access_requests_tenant_status', 'data_access_requests', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_data_access_requests_tenant_client', 'data_access_requests', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_data_access_requests_client_id'), 'data_access_requests', ['client_id'], unique=False)
    op.create_index(op.f('ix_data_access_requests_status'), 'data_access_requests', ['status'], unique=False)
    op.create_index(op.f('ix_data_access_requests_subject_id'), 'data_access_requests', ['subject_id'], unique=False)
    op.create_index(op.f('ix_data_access_requests_tenant_id'), 'data_access_requests', ['tenant_id'], unique=False)

    # Data Correction Requests
    op.create_table(
        'data_correction_requests',
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', 'APPLIED', 'FAILED', name='datacorrectionstatus', create_type=True), nullable=False, server_default='PENDING'),
        sa.Column('reviewed_by_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_by_id', sa.UUID(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['applied_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subject_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_correction_requests_tenant_subject', 'data_correction_requests', ['tenant_id', 'subject_id'], unique=False)
    op.create_index('ix_data_correction_requests_tenant_status', 'data_correction_requests', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_data_correction_requests_tenant_client', 'data_correction_requests', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_data_correction_requests_client_id'), 'data_correction_requests', ['client_id'], unique=False)
    op.create_index(op.f('ix_data_correction_requests_entity_id'), 'data_correction_requests', ['entity_id'], unique=False)
    op.create_index(op.f('ix_data_correction_requests_status'), 'data_correction_requests', ['status'], unique=False)
    op.create_index(op.f('ix_data_correction_requests_subject_id'), 'data_correction_requests', ['subject_id'], unique=False)
    op.create_index(op.f('ix_data_correction_requests_tenant_id'), 'data_correction_requests', ['tenant_id'], unique=False)

    # Data Erasure Requests
    op.create_table(
        'data_erasure_requests',
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('legal_basis', sa.String(length=255), nullable=True),
        sa.Column('external_refs', postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=False, server_default='{}'),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'IN_PROGRESS', 'COMPLETED', 'PARTIAL', 'FAILED', name='dataerasurestatus', create_type=True), nullable=False, server_default='PENDING'),
        sa.Column('approved_by_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('entities_affected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['subject_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_erasure_requests_tenant_subject', 'data_erasure_requests', ['tenant_id', 'subject_id'], unique=False)
    op.create_index('ix_data_erasure_requests_tenant_status', 'data_erasure_requests', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_data_erasure_requests_tenant_client', 'data_erasure_requests', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_data_erasure_requests_client_id'), 'data_erasure_requests', ['client_id'], unique=False)
    op.create_index(op.f('ix_data_erasure_requests_status'), 'data_erasure_requests', ['status'], unique=False)
    op.create_index(op.f('ix_data_erasure_requests_subject_id'), 'data_erasure_requests', ['subject_id'], unique=False)
    op.create_index(op.f('ix_data_erasure_requests_tenant_id'), 'data_erasure_requests', ['tenant_id'], unique=False)

    # Retention Policies
    op.create_table(
        'retention_policies',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='2555'),
        sa.Column('action', sa.Enum('DELETE', 'ARCHIVE', 'ANONYMIZE', name='retentionaction', create_type=True), nullable=False, server_default='DELETE'),
        sa.Column('protected', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('protection_reason', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_retention_policies_tenant_entity', 'retention_policies', ['tenant_id', 'entity_type'], unique=False)
    op.create_index('ix_retention_policies_tenant_active', 'retention_policies', ['tenant_id', 'is_active'], unique=False)
    op.create_index(op.f('ix_retention_policies_entity_type'), 'retention_policies', ['entity_type'], unique=False)
    op.create_index(op.f('ix_retention_policies_tenant_id'), 'retention_policies', ['tenant_id'], unique=False)

    # Retention Executions
    op.create_table(
        'retention_executions',
        sa.Column('policy_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('entities_affected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('entities_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['policy_id'], ['retention_policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_retention_executions_tenant_policy', 'retention_executions', ['tenant_id', 'policy_id'], unique=False)
    op.create_index('ix_retention_executions_tenant_status', 'retention_executions', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_retention_executions_executed_at', 'retention_executions', ['executed_at'], unique=False)
    op.create_index(op.f('ix_retention_executions_policy_id'), 'retention_executions', ['policy_id'], unique=False)
    op.create_index(op.f('ix_retention_executions_status'), 'retention_executions', ['status'], unique=False)
    op.create_index(op.f('ix_retention_executions_tenant_id'), 'retention_executions', ['tenant_id'], unique=False)

    # Data Residency Records
    op.create_table(
        'data_residency_records',
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('legal_basis', sa.String(length=255), nullable=True),
        sa.Column('data_categories', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by_id', sa.UUID(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_data_residency_tenant_entity', 'data_residency_records', ['tenant_id', 'entity_type', 'entity_id'], unique=False)
    op.create_index('ix_data_residency_tenant_region', 'data_residency_records', ['tenant_id', 'region'], unique=False)
    op.create_index(op.f('ix_data_residency_records_entity_id'), 'data_residency_records', ['entity_id'], unique=False)
    op.create_index(op.f('ix_data_residency_records_entity_type'), 'data_residency_records', ['entity_type'], unique=False)
    op.create_index(op.f('ix_data_residency_records_region'), 'data_residency_records', ['region'], unique=False)
    op.create_index(op.f('ix_data_residency_records_tenant_id'), 'data_residency_records', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('data_residency_records')
    op.drop_table('retention_executions')
    op.drop_table('retention_policies')
    op.drop_table('data_erasure_requests')
    op.drop_table('data_correction_requests')
    op.drop_table('data_access_requests')
    op.drop_table('dashboard_widgets')
    op.drop_table('report_schedules')
    op.drop_table('report_outputs')
    op.drop_table('report_jobs')
    op.drop_table('report_parameters')
    op.drop_table('report_definitions')
    op.drop_table('dashboard_widgets')