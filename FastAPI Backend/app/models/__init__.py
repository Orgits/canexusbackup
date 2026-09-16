# Central models import - ensures all models are registered with SQLAlchemy
# in the correct order before any mapper configuration happens.

# Core models (no dependencies)
from app.modules.assignments.models import (
    Assignment,
    AssignmentHistory,
    Escalation,
)

# Audit models
from app.modules.audit.models import AuditLog

# Billing models
from app.modules.billing.models import Expense, Invoice, InvoiceItem, Payment

# Calendar models
from app.modules.calendar.models import CalendarEvent

# Client models
from app.modules.clients.models import Client, ClientContact, ClientService
from app.modules.collaboration.models import (
    Comment,
    CommentAttachment,
    CommentReaction,
)

# Communication models
from app.modules.communications.models import Communication

# Compliance models
from app.modules.compliance.models import ComplianceApplicability, ComplianceCycle, ComplianceType

# Document models
from app.modules.documents.models import Document
from app.modules.firms.models import Firm

# Matter and task models
from app.modules.matters.models import Matter
from app.modules.mca_roc.models import (
    MCAFilingConfig,
    MCAFilingCycle,
)
from app.modules.notices.models import (
    Notice,
    NoticeEscalation,
)
from app.modules.notifications.models import (
    Notification,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
)
from app.modules.reviews.models import (
    ReviewComment,
    ReviewHistory,
    ReviewRequest,
)
from app.modules.tasks.models import Task
from app.modules.tds.models import (
    TDSChallan,
    TDSComplianceCycle,
    TDSDeductee,
)

# User and tenant models
from app.modules.users.models import Team, User

# Phase 2 models
from app.modules.workflow.models import (
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowTransitionDefinition,
    WorkflowTransitionHistory,
)
from app.modules.workload.models import (
    TeamCapacity,
    UserAvailability,
    WorkloadSnapshot,
    WorkloadSummary,
)

# Ensure all models are registered
__all__ = [
    "Assignment",
    "AssignmentHistory",
    "AuditLog",
    "CalendarEvent",
    "Client",
    "ClientContact",
    "ClientService",
    "Comment",
    "CommentAttachment",
    "CommentReaction",
    "Communication",
    "ComplianceApplicability",
    "ComplianceCycle",
    "ComplianceType",
    "Document",
    "Escalation",
    "Expense",
    "Firm",
    "Invoice",
    "InvoiceItem",
    "MCAFilingConfig",
    "MCAFilingCycle",
    "Matter",
    "Notice",
    "NoticeEscalation",
    "Notification",
    "NotificationDelivery",
    "NotificationPreference",
    "NotificationTemplate",
    "Payment",
    "ReviewComment",
    "ReviewHistory",
    "ReviewRequest",
    "TDSChallan",
    "TDSComplianceCycle",
    "TDSDeductee",
    "Task",
    "Team",
    "TeamCapacity",
    "User",
    "UserAvailability",
    "WorkflowDefinition",
    "WorkflowInstance",
    "WorkflowTransitionDefinition",
    "WorkflowTransitionHistory",
    "WorkloadSnapshot",
    "WorkloadSummary",
]
