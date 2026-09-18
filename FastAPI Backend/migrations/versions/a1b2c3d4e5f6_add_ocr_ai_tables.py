"""add_ocr_ai_tables

Revision ID: a1b2c3d4e5f6
Revises: 9e8d7c6b5a4f
Create Date: 2026-09-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '9e8d7c6b5a4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # OCR Templates
    op.create_table('ocr_templates',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('engine', sa.Enum('TESSERACT', 'AWS_TEXTRACT', 'GOOGLE_VISION', 'AZURE_FORM_RECOGNIZER', 'CUSTOM', name='ocrengine'), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False, default='eng'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('fields', sa.ARRAY(postgresql.JSONB(astext_type=sa.Text())), nullable=False, default=[]),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_templates_tenant_id'), 'ocr_templates', ['tenant_id'], unique=False)
    op.create_index('ix_ocr_templates_tenant_name', 'ocr_templates', ['tenant_id', 'name'], unique=False)

    # OCR Jobs
    op.create_table('ocr_jobs',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('engine', sa.Enum('TESSERACT', 'AWS_TEXTRACT', 'GOOGLE_VISION', 'AZURE_FORM_RECOGNIZER', 'CUSTOM', name='ocrengine'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='ocrstatus'), nullable=False, default='PENDING'),
        sa.Column('language', sa.String(length=10), nullable=False, default='eng'),
        sa.Column('pages_processed', sa.Integer(), nullable=False, default=0),
        sa.Column('total_pages', sa.Integer(), nullable=False, default=0),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('structured_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_jobs_document_id'), 'ocr_jobs', ['document_id'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_engine'), 'ocr_jobs', ['engine'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_status'), 'ocr_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_ocr_jobs_tenant_id'), 'ocr_jobs', ['tenant_id'], unique=False)
    op.create_index('ix_ocr_jobs_tenant_document', 'ocr_jobs', ['tenant_id', 'document_id'], unique=False)
    op.create_index('ix_ocr_jobs_tenant_status', 'ocr_jobs', ['tenant_id', 'status'], unique=False)
    op.create_index('ix_ocr_jobs_tenant_engine', 'ocr_jobs', ['tenant_id', 'engine'], unique=False)

    # AI Models
    op.create_table('ai_models',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model_type', sa.Enum('CLASSIFICATION', 'EXTRACTION', 'SUMMARIZATION', 'QUESTION_ANSWERING', 'SENTIMENT', 'ENTITY_RECOGNITION', 'CUSTOM', name='aimodeltype'), nullable=False),
        sa.Column('provider', sa.Enum('OPENAI', 'ANTHROPIC', 'GOOGLE', 'AZURE', 'HUGGINGFACE', 'LOCAL', 'CUSTOM', name='aimodelprovider'), nullable=False),
        sa.Column('model_name', sa.String(length=255), nullable=False),
        sa.Column('model_version', sa.String(length=100), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('credentials', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, default=60),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=False, default=1000),
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
    op.create_index(op.f('ix_ai_models_model_type'), 'ai_models', ['model_type'], unique=False)
    op.create_index(op.f('ix_ai_models_provider'), 'ai_models', ['provider'], unique=False)
    op.create_index(op.f('ix_ai_models_tenant_id'), 'ai_models', ['tenant_id'], unique=False)
    op.create_index('ix_ai_models_tenant_provider', 'ai_models', ['tenant_id', 'provider'], unique=False)
    op.create_index('ix_ai_models_tenant_type', 'ai_models', ['tenant_id', 'model_type'], unique=False)

    # AI Processing Jobs
    op.create_table('ai_processing_jobs',
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('model_id', sa.UUID(), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='aiprocessingstatus'), nullable=False, default='PENDING'),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=False, default=0),
        sa.Column('tokens_used', sa.Integer(), nullable=False, default=0),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, default='USD'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['model_id'], ['ai_models.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_processing_jobs_document_id'), 'ai_processing_jobs', ['document_id'], unique=False)
    op.create_index(op.f('ix_ai_processing_jobs_model_id'), 'ai_processing_jobs', ['model_id'], unique=False)
    op.create_index(op.f('ix_ai_processing_jobs_status'), 'ai_processing_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_ai_processing_jobs_tenant_id'), 'ai_processing_jobs', ['tenant_id'], unique=False)
    op.create_index('ix_ai_processing_jobs_tenant_document', 'ai_processing_jobs', ['tenant_id', 'document_id'], unique=False)
    op.create_index('ix_ai_processing_jobs_tenant_model', 'ai_processing_jobs', ['tenant_id', 'model_id'], unique=False)
    op.create_index('ix_ai_processing_jobs_tenant_status', 'ai_processing_jobs', ['tenant_id', 'status'], unique=False)

    # AI Confidence Thresholds
    op.create_table('ai_confidence_thresholds',
        sa.Column('model_type', sa.Enum('CLASSIFICATION', 'EXTRACTION', 'SUMMARIZATION', 'QUESTION_ANSWERING', 'SENTIMENT', 'ENTITY_RECOGNITION', 'CUSTOM', name='aimodeltype'), nullable=False),
        sa.Column('auto_approve_threshold', sa.Float(), nullable=False, default=0.95),
        sa.Column('auto_reject_threshold', sa.Float(), nullable=False, default=0.3),
        sa.Column('requires_review_threshold', sa.Float(), nullable=False, default=0.7),
        sa.Column('auto_approve_action', sa.String(length=50), nullable=False, default='approve'),
        sa.Column('auto_reject_action', sa.String(length=50), nullable=False, default='reject'),
        sa.Column('requires_review_action', sa.String(length=50), nullable=False, default='review'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_confidence_thresholds_model_type'), 'ai_confidence_thresholds', ['model_type'], unique=False)
    op.create_index(op.f('ix_ai_confidence_thresholds_tenant_id'), 'ai_confidence_thresholds', ['tenant_id'], unique=False)
    op.create_index('ix_ai_confidence_thresholds_tenant_type', 'ai_confidence_thresholds', ['tenant_id', 'model_type'], unique=False)

    # AI Review Tasks
    op.create_table('ai_review_tasks',
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('original_confidence', sa.Float(), nullable=True),
        sa.Column('final_confidence', sa.Float(), nullable=True),
        sa.Column('action_taken', sa.String(length=50), nullable=True),
        sa.Column('action_reason', sa.Text(), nullable=True),
        sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('updated_by', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['ai_processing_jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_review_tasks_job_id'), 'ai_review_tasks', ['job_id'], unique=False)
    op.create_index(op.f('ix_ai_review_tasks_assignee_id'), 'ai_review_tasks', ['assignee_id'], unique=False)
    op.create_index(op.f('ix_ai_review_tasks_status'), 'ai_review_tasks', ['status'], unique=False)
    op.create_index(op.f('ix_ai_review_tasks_tenant_id'), 'ai_review_tasks', ['tenant_id'], unique=False)
    op.create_index('ix_ai_review_tasks_tenant_job', 'ai_review_tasks', ['tenant_id', 'job_id'], unique=False)
    op.create_index('ix_ai_review_tasks_tenant_assignee', 'ai_review_tasks', ['tenant_id', 'assignee_id'], unique=False)
    op.create_index('ix_ai_review_tasks_tenant_status', 'ai_review_tasks', ['tenant_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_table('ai_review_tasks')
    op.drop_table('ai_confidence_thresholds')
    op.drop_table('ai_processing_jobs')
    op.drop_table('ai_models')
    op.drop_table('ocr_jobs')
    op.drop_table('ocr_templates')