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
    conn = op.get_bind()

    outbox_event_type = postgresql.ENUM(
        'compliance.cycle_created',
        'compliance.cycle_updated',
        'compliance.due_date_changed',
        'compliance.reminder_sent',
        'invoice.created',
        'invoice.updated',
        'invoice.sent',
        'invoice.paid',
        'invoice.voided',
        'payment.created',
        'payment.allocated',
        'payment.refunded',
        'task.created',
        'task.updated',
        'task.assigned',
        'task.completed',
        'task.status_changed',
        'workflow.transitioned',
        'workflow.instance_created',
        'workflow.instance_completed',
        'notification.created',
        'notification.sent',
        'notification.delivered',
        'notification.failed',
        'document.uploaded',
        'document.processed',
        'document.classified',
        'assignment.created',
        'assignment.reassigned',
        'assignment.escalated',
        name='outboxeventtype',
        create_type=False,
    )

    outbox_status = postgresql.ENUM(
        'pending',
        'processing',
        'processed',
        'failed',
        'dead_letter',
        name='outboxstatus',
        create_type=False,
    )

    for enum_type in [outbox_event_type, outbox_status]:
        try:
            enum_type.create(conn, checkfirst=True)
        except Exception:
            pass

    op.create_table(
        'outbox_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', outbox_event_type, nullable=False),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('status', outbox_status, nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(255), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('ix_outbox_events_tenant_status', 'outbox_events', ['tenant_id', 'status'])
    op.create_index('ix_outbox_events_tenant_type', 'outbox_events', ['tenant_id', 'event_type'])
    op.create_index('ix_outbox_events_tenant_aggregate', 'outbox_events', ['tenant_id', 'aggregate_type', 'aggregate_id'])
    op.create_index('ix_outbox_events_created', 'outbox_events', ['created_at'])
    op.create_index('ix_outbox_events_status_retry', 'outbox_events', ['status', 'retry_count'])
    op.create_index('ix_outbox_events_idempotency_key', 'outbox_events', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_outbox_events_idempotency_key', table_name='outbox_events')
    op.drop_index('ix_outbox_events_status_retry', table_name='outbox_events')
    op.drop_index('ix_outbox_events_created', table_name='outbox_events')
    op.drop_index('ix_outbox_events_tenant_aggregate', table_name='outbox_events')
    op.drop_index('ix_outbox_events_tenant_type', table_name='outbox_events')
    op.drop_index('ix_outbox_events_tenant_status', table_name='outbox_events')
    op.drop_table('outbox_events')

    conn = op.get_bind()
    outbox_status = postgresql.ENUM(name='outboxstatus')
    outbox_event_type = postgresql.ENUM(name='outboxeventtype')
    try:
        outbox_status.drop(conn, checkfirst=True)
    except Exception:
        pass
    try:
        outbox_event_type.drop(conn, checkfirst=True)
    except Exception:
        pass