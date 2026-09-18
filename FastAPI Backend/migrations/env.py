from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.core.database.base import Base

# Import all models to ensure they are registered with Base.metadata
from app.modules.firms.models import Firm
from app.modules.users.models import User, Team
from app.modules.clients.models import Client, ClientContact, ClientService
from app.modules.matters.models import Matter
from app.modules.tasks.models import Task
from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceApplicability
from app.modules.documents.models import Document
from app.modules.billing.models import Invoice, InvoiceItem, Payment, Expense
from app.modules.calendar.models import CalendarEvent
from app.modules.audit.models import AuditLog
from app.modules.communications.models import Communication

# Phase 2 modules
from app.modules.workflow.models import (
    WorkflowDefinition,
    WorkflowTransitionDefinition,
    WorkflowInstance,
    WorkflowTransitionHistory,
)
from app.modules.reviews.models import (
    ReviewRequest,
    ReviewComment,
    ReviewHistory,
)
from app.modules.tds.models import (
    TDSComplianceCycle,
    TDSChallan,
    TDSDeductee,
)
from app.modules.mca_roc.models import (
    MCAFilingCycle,
    MCAFilingConfig,
)
from app.modules.notices.models import (
    Notice,
    NoticeEscalation,
)
from app.modules.workload.models import (
    UserAvailability,
    TeamCapacity,
    WorkloadSnapshot,
    WorkloadSummary,
)
from app.modules.assignments.models import (
    Assignment,
    AssignmentHistory,
    Escalation,
)
from app.modules.collaboration.models import (
    Comment,
    CommentAttachment,
    CommentReaction,
)
from app.modules.notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationDelivery,
    NotificationPreference,
)

# Phase 3 modules
from app.modules.campaigns.models import Campaign, CampaignRecipient
from app.modules.conversations.models import Conversation, ConversationMessage
from app.modules.templates.models import Template
from app.modules.consent.models import Consent, ConsentTemplate
from app.modules.suppression.models import Suppression
from app.modules.document_requests.models import DocumentRequest, DocumentRequestDocument
from app.modules.channels.models import ChannelProvider, MessageLog
from app.modules.webhooks.models import WebhookEvent, WebhookEndpoint
from app.modules.ocr.models import OCRJob, OCRTemplate
from app.modules.ai_processing.models import AIModel, AIProcessingJob, AIConfidenceThreshold, AIReviewTask

# Phase 4 modules
from app.modules.audit_workspace.models import (
    AuditEngagement,
    AuditWorkingPaper,
    AuditEvidence,
    AuditReview,
    AuditSignOff,
)

config = context.config

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()