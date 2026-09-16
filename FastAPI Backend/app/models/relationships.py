"""Model relationship setup - called after all models are loaded."""

from sqlalchemy.orm import relationship

from app.modules.firms.models import Firm


def setup_firm_relationships():
    """Set up Firm relationships after all models are loaded."""
    Firm.users = relationship("User", lazy="dynamic")
    Firm.teams = relationship("Team", lazy="dynamic")
    Firm.clients = relationship("Client", lazy="dynamic")
    Firm.client_contacts = relationship("ClientContact", lazy="dynamic")
    Firm.client_services = relationship("ClientService", lazy="dynamic")
    Firm.matters = relationship("Matter", lazy="dynamic")
    Firm.tasks = relationship("Task", lazy="dynamic")
    Firm.compliance_types = relationship("ComplianceType", lazy="dynamic")
    Firm.compliance_cycles = relationship("ComplianceCycle", lazy="dynamic")
    Firm.compliance_applicability = relationship("ComplianceApplicability", lazy="dynamic")
    Firm.documents = relationship("Document", lazy="dynamic")
    Firm.invoices = relationship("Invoice", lazy="dynamic")
    Firm.invoice_items = relationship("InvoiceItem", lazy="dynamic")
    Firm.payments = relationship("Payment", lazy="dynamic")
    Firm.expenses = relationship("Expense", lazy="dynamic")
    Firm.calendar_events = relationship("CalendarEvent", lazy="dynamic")
    Firm.communications = relationship("Communication", lazy="dynamic")
    Firm.workflow_definitions = relationship("WorkflowDefinition", lazy="dynamic")
    Firm.workflow_transition_definitions = relationship("WorkflowTransitionDefinition", lazy="dynamic")
    Firm.workflow_instances = relationship("WorkflowInstance", lazy="dynamic")
    Firm.workflow_transition_history = relationship("WorkflowTransitionHistory", lazy="dynamic")
    Firm.review_requests = relationship("ReviewRequest", lazy="dynamic")
    Firm.review_comments = relationship("ReviewComment", lazy="dynamic")
    Firm.review_history = relationship("ReviewHistory", lazy="dynamic")
    Firm.tds_compliance_cycles = relationship("TDSComplianceCycle", lazy="dynamic")
    Firm.tds_challans = relationship("TDSChallan", lazy="dynamic")
    Firm.tds_deductees = relationship("TDSDeductee", lazy="dynamic")
    Firm.mca_filing_cycles = relationship("MCAFilingCycle", lazy="dynamic")
    Firm.mca_filing_configs = relationship("MCAFilingConfig", lazy="dynamic")
    Firm.notices = relationship("Notice", lazy="dynamic")
    Firm.notice_escalations = relationship("NoticeEscalation", lazy="dynamic")
    Firm.user_availability = relationship("UserAvailability", lazy="dynamic")
    Firm.team_capacity = relationship("TeamCapacity", lazy="dynamic")
    Firm.workload_snapshots = relationship("WorkloadSnapshot", lazy="dynamic")
    Firm.workload_summaries = relationship("WorkloadSummary", lazy="dynamic")
    Firm.assignments = relationship("Assignment", lazy="dynamic")
    Firm.assignment_history = relationship("AssignmentHistory", lazy="dynamic")
    Firm.escalations = relationship("Escalation", lazy="dynamic")
    Firm.comments = relationship("Comment", lazy="dynamic")
    Firm.comment_attachments = relationship("CommentAttachment", lazy="dynamic")
    Firm.comment_reactions = relationship("CommentReaction", lazy="dynamic")
    Firm.notification_templates = relationship("NotificationTemplate", lazy="dynamic")
    Firm.notifications = relationship("Notification", lazy="dynamic")
    Firm.notification_deliveries = relationship("NotificationDelivery", lazy="dynamic")
    Firm.notification_preferences = relationship("NotificationPreference", lazy="dynamic")
    Firm.audit_logs = relationship("AuditLog", lazy="dynamic")


def setup_all_relationships():
    """Set up all model relationships after all models are loaded."""
    setup_firm_relationships()
