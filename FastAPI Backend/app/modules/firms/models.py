import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, UUIDMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.users.models import User, Team
    from app.modules.clients.models import Client, ClientContact, ClientService
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceApplicability
    from app.modules.documents.models import Document
    from app.modules.billing.models import Invoice, InvoiceItem, Payment, Expense
    from app.modules.calendar.models import CalendarEvent
    from app.modules.communications.models import Communication
    from app.modules.workflow.models import WorkflowDefinition, WorkflowTransitionDefinition, WorkflowInstance, WorkflowTransitionHistory
    from app.modules.reviews.models import ReviewRequest, ReviewComment, ReviewHistory
    from app.modules.tds.models import TDSComplianceCycle, TDSChallan, TDSDeductee
    from app.modules.mca_roc.models import MCAFilingCycle, MCAFilingConfig
    from app.modules.notices.models import Notice, NoticeEscalation
    from app.modules.workload.models import UserAvailability, TeamCapacity, WorkloadSnapshot, WorkloadSummary
    from app.modules.assignments.models import Assignment, AssignmentHistory, Escalation
    from app.modules.collaboration.models import Comment, CommentAttachment, CommentReaction
    from app.modules.notifications.models import NotificationTemplate, Notification, NotificationDelivery, NotificationPreference
    from app.modules.audit.models import AuditLog


class Firm(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "firms"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    settings: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    users = relationship("User", back_populates="tenant", lazy="dynamic")
    teams = relationship("Team", back_populates="tenant", lazy="dynamic")
    clients = relationship("Client", back_populates="tenant", lazy="dynamic")
    client_contacts = relationship("ClientContact", back_populates="tenant", lazy="dynamic")
    client_services = relationship("ClientService", back_populates="tenant", lazy="dynamic")
    matters = relationship("Matter", back_populates="tenant", lazy="dynamic")
    tasks = relationship("Task", back_populates="tenant", lazy="dynamic")
    compliance_types = relationship("ComplianceType", back_populates="tenant", lazy="dynamic")
    compliance_cycles = relationship("ComplianceCycle", back_populates="tenant", lazy="dynamic")
    compliance_applicability = relationship("ComplianceApplicability", back_populates="tenant", lazy="dynamic")
    documents = relationship("Document", back_populates="tenant", lazy="dynamic")
    invoices = relationship("Invoice", back_populates="tenant", lazy="dynamic")
    invoice_items = relationship("InvoiceItem", back_populates="tenant", lazy="dynamic")
    payments = relationship("Payment", back_populates="tenant", lazy="dynamic")
    expenses = relationship("Expense", back_populates="tenant", lazy="dynamic")
    calendar_events = relationship("CalendarEvent", back_populates="tenant", lazy="dynamic")
    communications = relationship("Communication", back_populates="tenant", lazy="dynamic")
    workflow_definitions = relationship("WorkflowDefinition", back_populates="tenant", lazy="dynamic")
    workflow_transition_definitions = relationship("WorkflowTransitionDefinition", back_populates="tenant", lazy="dynamic")
    workflow_instances = relationship("WorkflowInstance", back_populates="tenant", lazy="dynamic")
    workflow_transition_history = relationship("WorkflowTransitionHistory", back_populates="tenant", lazy="dynamic")
    review_requests = relationship("ReviewRequest", back_populates="tenant", lazy="dynamic")
    review_comments = relationship("ReviewComment", back_populates="tenant", lazy="dynamic")
    review_history = relationship("ReviewHistory", back_populates="tenant", lazy="dynamic")
    tds_compliance_cycles = relationship("TDSComplianceCycle", back_populates="tenant", lazy="dynamic")
    tds_challans = relationship("TDSChallan", back_populates="tenant", lazy="dynamic")
    tds_deductees = relationship("TDSDeductee", back_populates="tenant", lazy="dynamic")
    mca_filing_cycles = relationship("MCAFilingCycle", back_populates="tenant", lazy="dynamic")
    mca_filing_configs = relationship("MCAFilingConfig", back_populates="tenant", lazy="dynamic")
    notices = relationship("Notice", back_populates="tenant", lazy="dynamic")
    notice_escalations = relationship("NoticeEscalation", back_populates="tenant", lazy="dynamic")
    user_availability = relationship("UserAvailability", back_populates="tenant", lazy="dynamic")
    team_capacity = relationship("TeamCapacity", back_populates="tenant", lazy="dynamic")
    workload_snapshots = relationship("WorkloadSnapshot", back_populates="tenant", lazy="dynamic")
    workload_summaries = relationship("WorkloadSummary", back_populates="tenant", lazy="dynamic")
    assignments = relationship("Assignment", back_populates="tenant", lazy="dynamic")
    assignment_history = relationship("AssignmentHistory", back_populates="tenant", lazy="dynamic")
    escalations = relationship("Escalation", back_populates="tenant", lazy="dynamic")
    comments = relationship("Comment", back_populates="tenant", lazy="dynamic")
    comment_attachments = relationship("CommentAttachment", back_populates="tenant", lazy="dynamic")
    comment_reactions = relationship("CommentReaction", back_populates="tenant", lazy="dynamic")
    notification_templates = relationship("NotificationTemplate", back_populates="tenant", lazy="dynamic")
    notifications = relationship("Notification", back_populates="tenant", lazy="dynamic")
    notification_deliveries = relationship("NotificationDelivery", back_populates="tenant", lazy="dynamic")
    notification_preferences = relationship("NotificationPreference", back_populates="tenant", lazy="dynamic")
    audit_logs = relationship("AuditLog", back_populates="tenant", lazy="dynamic")