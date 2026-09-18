"""add_phase3_tables

Revision ID: 7a3b9c1f2e4d
Revises: fd590f5fb5fa
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7a3b9c1f2e4d'
down_revision: Union[str, None] = 'fd590f5fb5fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Channel Providers
    op.create_table('channel_providers',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('channel_type', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'VOICE', 'PUSH', name='channeltype'), nullable=False),
        sa.Column('provider_name', sa.String(length=100), nullable=False),
        sa.Column('provider_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'ERROR', 'PENDING', name='providerstatus'), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('webhook_url', sa.String(length=500), nullable=True),
        sa.Column('webhook_secret', sa.String(length=255), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, default=60),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False, default=1000),
        sa.Column('rate_limit_per_day', sa.Integer(), nullable=False, default=10000),
        sa.Column('last_health_check', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('error_count', sa.Integer(), nullable=False, default=0),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
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
    op.create_index(op.f('ix_channel_providers_channel_type'), 'channel_providers', ['channel_type'], unique=False)
    op.create_index(op.f('ix_channel_providers_status'), 'channel_providers', ['status'], unique=False)
    op.create_index(op.f('ix_channel_providers_tenant_id'), 'channel_providers', ['tenant_id'], unique=False)
    op.create_index('ix_channel_providers_tenant_status', 'channel_providers', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_channel_providers_tenant_type', 'channel_providers', ['tenant_id', 'channel_type'], unique=False)

    # Consent Templates
    op.create_table('consent_templates',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('channel', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'CALL', 'POST', 'ALL', name='consentchannel'), nullable=False),
        sa.Column('consent_text', sa.Text(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False, default='1.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('language', sa.String(length=10), nullable=False, default='en'),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
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
    op.create_index(op.f('ix_consent_templates_channel'), 'consent_templates', ['channel'], unique=False)
    op.create_index('ix_consent_templates_tenant_channel', 'consent_templates', ['tenant_id', 'channel'], unique=False)
    op.create_index(op.f('ix_consent_templates_tenant_id'), 'consent_templates', ['tenant_id'], unique=False)

    # Templates
    op.create_table('templates',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'DOCUMENT', 'NOTIFICATION', 'GENERIC', name='templatecategory'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'ACTIVE', 'ARCHIVED', name='templatestatus'), nullable=False, default='DRAFT'),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('variables', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, default='en'),
        sa.Column('version', sa.Integer(), nullable=False, default=1),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
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
    op.create_index(op.f('ix_templates_category'), 'templates', ['category'], unique=False)
    op.create_index(op.f('ix_templates_channel'), 'templates', ['channel'], unique=False)
    op.create_index(op.f('ix_templates_status'), 'templates', ['status'], unique=False)
    op.create_index('ix_templates_tenant_category', 'templates', ['tenant_id', 'category'], unique=False)
    op.create_index(op.f('ix_templates_tenant_id'), 'templates', ['tenant_id'], unique=False)
    op.create_index('ix_templates_tenant_name', 'templates', ['tenant_id', 'name'], unique=False)
    op.create_index('ix_templates_tenant_status', 'templates', ['tenant_id', 'status'], unique=False)

    # Webhook Endpoints
    op.create_table('webhook_endpoints',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('secret', sa.String(length=255), nullable=True),
        sa.Column('events', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('secret_verification', sa.Boolean(), nullable=False, default=True),
        sa.Column('retry_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, default=30),
        sa.Column('success_count', sa.Integer(), nullable=False, default=0),
        sa.Column('failure_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('secret_key', sa.String(length=255), nullable=True),
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
    op.create_index(op.f('ix_webhook_endpoints_tenant_id'), 'webhook_endpoints', ['tenant_id'], unique=False)
    op.create_index('ix_webhook_endpoints_tenant_url', 'webhook_endpoints', ['tenant_id', 'url'], unique=False)

    # Webhook Events
    op.create_table('webhook_events',
        sa.Column('source', sa.Enum('WHATSAPP', 'EMAIL', 'SMS', 'DOCUMENT', 'PAYMENT', 'CUSTOM', name='webhooksource'), nullable=False),
        sa.Column('external_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', sa.String(length=100), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('raw_payload', sa.Text(), nullable=True),
        sa.Column('headers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('query_params', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('status', sa.String(length=50), nullable=False, default='received'),
        sa.Column('processing_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer(), nullable=False, default=3),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_by', sa.UUID(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('retry_after', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_events_event_category'), 'webhook_events', ['event_category'], unique=False)
    op.create_index(op.f('ix_webhook_events_event_type'), 'webhook_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhook_events_external_id'), 'webhook_events', ['external_id'], unique=False)
    op.create_index(op.f('ix_webhook_events_idempotency_key'), 'webhook_events', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_webhook_events_source'), 'webhook_events', ['source'], unique=False)
    op.create_index(op.f('ix_webhook_events_status'), 'webhook_events', ['status'], unique=False)
    op.create_index('ix_webhook_events_tenant_created', 'webhook_events', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_webhook_events_tenant_external_id', 'webhook_events', ['tenant_id', 'external_id'], unique=False)
    op.create_index(op.f('ix_webhook_events_tenant_id'), 'webhook_events', ['tenant_id'], unique=False)
    op.create_index('ix_webhook_events_tenant_source', 'webhook_events', ['tenant_id', 'source'], unique=False)
    op.create_index('ix_webhook_events_tenant_status', 'webhook_events', ['tenant_id', 'status'], unique=False)

    # Campaigns
    op.create_table('campaigns',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('campaign_type', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'MIXED', name='campaigntype'), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'SCHEDULED', 'SENDING', 'SENT', 'COMPLETED', 'FAILED', 'CANCELLED', 'PAUSED', name='campaignstatus'), nullable=False, default='DRAFT'),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('audience_filter', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('audience_count', sa.Integer(), nullable=False, default=0),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_count', sa.Integer(), nullable=False, default=0),
        sa.Column('delivered_count', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_count', sa.Integer(), nullable=False, default=0),
        sa.Column('opened_count', sa.Integer(), nullable=False, default=0),
        sa.Column('clicked_count', sa.Integer(), nullable=False, default=0),
        sa.Column('replied_count', sa.Integer(), nullable=False, default=0),
        sa.Column('bounced_count', sa.Integer(), nullable=False, default=0),
        sa.Column('unsubscribed_count', sa.Integer(), nullable=False, default=0),
        sa.Column('total_cost', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('cost_per_message', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('settings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaigns_campaign_type'), 'campaigns', ['campaign_type'], unique=False)
    op.create_index(op.f('ix_campaigns_scheduled_at'), 'campaigns', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)
    op.create_index(op.f('ix_campaigns_template_id'), 'campaigns', ['template_id'], unique=False)
    op.create_index(op.f('ix_campaigns_tenant_id'), 'campaigns', ['tenant_id'], unique=False)
    op.create_index('ix_campaigns_tenant_scheduled', 'campaigns', ['tenant_id', 'scheduled_at'], unique=False)
    op.create_index('ix_campaigns_tenant_status', 'campaigns', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_campaigns_tenant_type', 'campaigns', ['tenant_id', 'campaign_type'], unique=False)

    # Consents
    op.create_table('consents',
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('channel', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'CALL', 'POST', 'ALL', name='consentchannel'), nullable=False),
        sa.Column('status', sa.Enum('GIVEN', 'WITHDRAWN', 'EXPIRED', 'PENDING', name='consentstatus'), nullable=False, default='PENDING'),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('consent_text', sa.Text(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False, default='1.0'),
        sa.Column('given_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_consents_channel'), 'consents', ['channel'], unique=False)
    op.create_index(op.f('ix_consents_client_id'), 'consents', ['client_id'], unique=False)
    op.create_index(op.f('ix_consents_given_at'), 'consents', ['given_at'], unique=False)
    op.create_index(op.f('ix_consents_status'), 'consents', ['status'], unique=False)
    op.create_index('ix_consents_tenant_channel', 'consents', ['tenant_id', 'channel'], unique=False)
    op.create_index('ix_consents_tenant_client', 'consents', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_consents_tenant_id'), 'consents', ['tenant_id'], unique=False)
    op.create_index('ix_consents_tenant_status', 'consents', ['tenant_id', 'status'], unique=False)

    # Conversations
    op.create_table('conversations',
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', 'ARCHIVED', 'PENDING', name='conversationstatus'), nullable=False, default='OPEN'),
        sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'URGENT', name='conversationpriority'), nullable=False, default='NORMAL'),
        sa.Column('channel', sa.String(length=50), nullable=True),
        sa.Column('participant_ids', sa.ARRAY(sa.UUID()), nullable=False, default=[]),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by', sa.UUID(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_preview', sa.String(length=500), nullable=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_assignee_id'), 'conversations', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_conversations_channel'), 'conversations', ['channel'], unique=False)
    op.create_index(op.f('ix_conversations_client_id'), 'conversations', ['client_id'], unique=False)
    op.create_index(op.f('ix_conversations_last_message_at'), 'conversations', ['last_message_at'], unique=False)
    op.create_index(op.f('ix_conversations_status'), 'conversations', ['status'], unique=False)
    op.create_index('ix_conversations_tenant_assignee', 'conversations', ['tenant_id', 'assignee_id'], unique=False)
    op.create_index('ix_conversations_tenant_client', 'conversations', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_conversations_tenant_id'), 'conversations', ['tenant_id'], unique=False)
    op.create_index('ix_conversations_tenant_status', 'conversations', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_conversations_tenant_updated', 'conversations', ['tenant_id', 'updated_at'], unique=False)

    # Document Requests
    op.create_table('document_requests',
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('matter_id', sa.UUID(), nullable=True),
        sa.Column('assigned_to', sa.UUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'SENT', 'VIEWED', 'IN_PROGRESS', 'SUBMITTED', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED', name='documentrequeststatus'), nullable=False, default='DRAFT'),
        sa.Column('priority', sa.Enum('LOW', 'NORMAL', 'HIGH', 'URGENT', name='documentrequestpriority'), nullable=False, default='NORMAL'),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('required_documents', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('submitted_documents', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default=[]),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.UUID(), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_count', sa.Integer(), nullable=False, default=0),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matter_id'], ['matters.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_requests_assigned_to'), 'document_requests', ['assigned_to'], unique=False)
    op.create_index(op.f('ix_document_requests_client_id'), 'document_requests', ['client_id'], unique=False)
    op.create_index(op.f('ix_document_requests_due_date'), 'document_requests', ['due_date'], unique=False)
    op.create_index(op.f('ix_document_requests_matter_id'), 'document_requests', ['matter_id'], unique=False)
    op.create_index(op.f('ix_document_requests_status'), 'document_requests', ['status'], unique=False)
    op.create_index('ix_document_requests_tenant_client', 'document_requests', ['tenant_id', 'client_id'], unique=False)
    op.create_index('ix_document_requests_tenant_due', 'document_requests', ['tenant_id', 'due_date'], unique=False)
    op.create_index(op.f('ix_document_requests_tenant_id'), 'document_requests', ['tenant_id'], unique=False)
    op.create_index('ix_document_requests_tenant_status', 'document_requests', ['tenant_id', 'status'], unique=False)

    # Message Logs
    op.create_table('message_logs',
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('channel_type', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=500), nullable=False),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, default='USD'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['channel_providers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_logs_channel_type'), 'message_logs', ['channel_type'], unique=False)
    op.create_index(op.f('ix_message_logs_provider_id'), 'message_logs', ['provider_id'], unique=False)
    op.create_index(op.f('ix_message_logs_provider_message_id'), 'message_logs', ['provider_message_id'], unique=False)
    op.create_index(op.f('ix_message_logs_recipient'), 'message_logs', ['recipient'], unique=False)
    op.create_index(op.f('ix_message_logs_status'), 'message_logs', ['status'], unique=False)
    op.create_index('ix_message_logs_tenant_channel', 'message_logs', ['tenant_id', 'channel_type'], unique=False)
    op.create_index('ix_message_logs_tenant_created', 'message_logs', ['tenant_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_message_logs_tenant_id'), 'message_logs', ['tenant_id'], unique=False)
    op.create_index('ix_message_logs_tenant_provider', 'message_logs', ['tenant_id', 'provider_id'], unique=False)
    op.create_index('ix_message_logs_tenant_recipient', 'message_logs', ['tenant_id', 'recipient'], unique=False)
    op.create_index('ix_message_logs_tenant_status', 'message_logs', ['tenant_id', 'status'], unique=False)

    # Suppressions
    op.create_table('suppressions',
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('channel', sa.Enum('EMAIL', 'WHATSAPP', 'SMS', 'CALL', 'POST', 'ALL', name='suppressionchannel'), nullable=False),
        sa.Column('reason', sa.Enum('UNSUBSCRIBED', 'BOUNCED', 'COMPLAINT', 'MANUAL', 'LEGAL', 'DO_NOT_CONTACT', name='suppressionreason'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=False),
        sa.Column('source_reference', sa.String(length=255), nullable=True),
        sa.Column('client_id', sa.UUID(), nullable=True),
        sa.Column('is_global', sa.Boolean(), nullable=False, default=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_suppressions_channel'), 'suppressions', ['channel'], unique=False)
    op.create_index(op.f('ix_suppressions_client_id'), 'suppressions', ['client_id'], unique=False)
    op.create_index(op.f('ix_suppressions_expires_at'), 'suppressions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_suppressions_reason'), 'suppressions', ['reason'], unique=False)
    op.create_index('ix_suppressions_tenant_channel', 'suppressions', ['tenant_id', 'channel'], unique=False)
    op.create_index(op.f('ix_suppressions_tenant_id'), 'suppressions', ['tenant_id'], unique=False)
    op.create_index('ix_suppressions_tenant_reason', 'suppressions', ['tenant_id', 'reason'], unique=False)
    op.create_index('ix_suppressions_tenant_value', 'suppressions', ['tenant_id', 'value'], unique=False)
    op.create_index(op.f('ix_suppressions_value'), 'suppressions', ['value'], unique=False)

    # Campaign Recipients
    op.create_table('campaign_recipients',
        sa.Column('campaign_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('communication_id', sa.UUID(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('replied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('bounced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unsubscribed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_campaign_recipients_campaign_id'), 'campaign_recipients', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_campaign_recipients_client_id'), 'campaign_recipients', ['client_id'], unique=False)
    op.create_index(op.f('ix_campaign_recipients_communication_id'), 'campaign_recipients', ['communication_id'], unique=False)
    op.create_index(op.f('ix_campaign_recipients_status'), 'campaign_recipients', ['status'], unique=False)
    op.create_index('ix_campaign_recipients_tenant_campaign', 'campaign_recipients', ['tenant_id', 'campaign_id'], unique=False)
    op.create_index('ix_campaign_recipients_tenant_client', 'campaign_recipients', ['tenant_id', 'client_id'], unique=False)
    op.create_index(op.f('ix_campaign_recipients_tenant_id'), 'campaign_recipients', ['tenant_id'], unique=False)
    op.create_index('ix_campaign_recipients_tenant_status', 'campaign_recipients', ['tenant_id', 'status'], unique=False)

    # Conversation Messages
    op.create_table('conversation_messages',
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('sender_id', sa.UUID(), nullable=True),
        sa.Column('sender_type', sa.String(length=50), nullable=False, default='user'),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_html', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=True),
        sa.Column('from_address', sa.String(length=255), nullable=True),
        sa.Column('to_addresses', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('cc_addresses', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('bcc_addresses', sa.ARRAY(sa.String()), nullable=False, default=[]),
        sa.Column('attachment_ids', sa.ARRAY(sa.UUID()), nullable=False, default=[]),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('provider_message_id', sa.String(length=255), nullable=True),
        sa.Column('provider_status', sa.String(length=50), nullable=True),
        sa.Column('provider_response', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_messages_channel'), 'conversation_messages', ['channel'], unique=False)
    op.create_index(op.f('ix_conversation_messages_conversation_id'), 'conversation_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_provider_message_id'), 'conversation_messages', ['provider_message_id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_sender_id'), 'conversation_messages', ['sender_id'], unique=False)
    op.create_index(op.f('ix_conversation_messages_sent_at'), 'conversation_messages', ['sent_at'], unique=False)
    op.create_index('ix_conversation_messages_tenant_conversation', 'conversation_messages', ['tenant_id', 'conversation_id'], unique=False)
    op.create_index('ix_conversation_messages_tenant_created', 'conversation_messages', ['tenant_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_conversation_messages_tenant_id'), 'conversation_messages', ['tenant_id'], unique=False)
    op.create_index('ix_conversation_messages_tenant_sender', 'conversation_messages', ['tenant_id', 'sender_id'], unique=False)

    # Document Request Documents
    op.create_table('document_request_documents',
        sa.Column('request_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('document_name', sa.String(length=500), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, default=True),
        sa.Column('uploaded_by', sa.UUID(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['document_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_doc_request_docs_tenant_request', 'document_request_documents', ['tenant_id', 'request_id'], unique=False)
    op.create_index(op.f('ix_document_request_documents_document_id'), 'document_request_documents', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_request_documents_request_id'), 'document_request_documents', ['request_id'], unique=False)
    op.create_index(op.f('ix_document_request_documents_tenant_id'), 'document_request_documents', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_table('document_request_documents')
    op.drop_table('conversation_messages')
    op.drop_table('campaign_recipients')
    op.drop_table('suppressions')
    op.drop_table('message_logs')
    op.drop_table('document_requests')
    op.drop_table('conversations')
    op.drop_table('consents')
    op.drop_table('campaigns')
    op.drop_table('webhook_events')
    op.drop_table('webhook_endpoints')
    op.drop_table('templates')
    op.drop_table('consent_templates')
    op.drop_table('channel_providers')