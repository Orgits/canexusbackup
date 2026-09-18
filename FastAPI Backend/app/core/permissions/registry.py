from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    CLIENTS_READ = "clients.read"
    CLIENTS_CREATE = "clients.create"
    CLIENTS_UPDATE = "clients.update"
    CLIENTS_DELETE = "clients.delete"

    MATTERS_READ = "matters.read"
    MATTERS_CREATE = "matters.create"
    MATTERS_UPDATE = "matters.update"
    MATTERS_DELETE = "matters.delete"

    TASKS_READ = "tasks.read"
    TASKS_CREATE = "tasks.create"
    TASKS_UPDATE = "tasks.update"
    TASKS_DELETE = "tasks.delete"

    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_DELETE = "documents.delete"

    BILLING_READ = "billing.read"
    BILLING_MANAGE = "billing.manage"

    COMPLIANCE_READ = "compliance.read"
    COMPLIANCE_CREATE = "compliance.create"
    COMPLIANCE_UPDATE = "compliance.update"
    COMPLIANCE_DELETE = "compliance.delete"

    ADMIN_USERS_MANAGE = "admin.users.manage"
    ADMIN_ROLES_MANAGE = "admin.roles.manage"
    ADMIN_FIRM_MANAGE = "admin.firm.manage"

    AUDIT_READ = "audit.read"
    AUDIT_MANAGE = "audit.manage"

    # Phase 2 - Workflow Engine
    WORKFLOW_READ = "workflow.read"
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_UPDATE = "workflow.update"
    WORKFLOW_DELETE = "workflow.delete"
    WORKFLOW_TRANSITION = "workflow.transition"

    # Phase 2 - Review & Approval Engine
    REVIEWS_READ = "reviews.read"
    REVIEWS_CREATE = "reviews.create"
    REVIEWS_UPDATE = "reviews.update"
    REVIEWS_DELETE = "reviews.delete"
    REVIEWS_TRANSITION = "reviews.transition"
    REVIEWS_COMMENT = "reviews.comment"

    # Phase 2 - TDS
    TDS_READ = "tds.read"
    TDS_CREATE = "tds.create"
    TDS_UPDATE = "tds.update"
    TDS_DELETE = "tds.delete"
    TDS_TRANSITION = "tds.transition"

    # Phase 2 - MCA/ROC
    MCA_ROC_READ = "mca_roc.read"
    MCA_ROC_CREATE = "mca_roc.create"
    MCA_ROC_UPDATE = "mca_roc.update"
    MCA_ROC_DELETE = "mca_roc.delete"
    MCA_ROC_TRANSITION = "mca_roc.transition"

    # Phase 2 - Notices
    NOTICES_READ = "notices.read"
    NOTICES_CREATE = "notices.create"
    NOTICES_UPDATE = "notices.update"
    NOTICES_DELETE = "notices.delete"
    NOTICES_TRANSITION = "notices.transition"
    NOTICES_ESCALATE = "notices.escalate"

    # Phase 2 - Workload
    WORKLOAD_READ = "workload.read"
    WORKLOAD_UPDATE = "workload.update"

    # Phase 2 - Assignments
    ASSIGNMENTS_READ = "assignments.read"
    ASSIGNMENTS_CREATE = "assignments.create"
    ASSIGNMENTS_UPDATE = "assignments.update"
    ASSIGNMENTS_REASSIGN = "assignments.reassign"
    ASSIGNMENTS_ESCALATE = "assignments.escalate"

    # Phase 2 - Collaboration
    COLLABORATION_READ = "collaboration.read"
    COLLABORATION_COMMENT = "collaboration.comment"

    # Phase 2 - Notifications
    NOTIFICATIONS_READ = "notifications.read"
    NOTIFICATIONS_CREATE = "notifications.create"
    NOTIFICATIONS_UPDATE = "notifications.update"
    NOTIFICATIONS_DELETE = "notifications.delete"

    # Phase 3 - Communications
    COMMUNICATIONS_READ = "communications.read"
    COMMUNICATIONS_CREATE = "communications.create"
    COMMUNICATIONS_UPDATE = "communications.update"
    COMMUNICATIONS_DELETE = "communications.delete"
    COMMUNICATIONS_SEND = "communications.send"

    # Phase 3 - Conversations
    CONVERSATIONS_READ = "conversations.read"
    CONVERSATIONS_CREATE = "conversations.create"
    CONVERSATIONS_UPDATE = "conversations.update"
    CONVERSATIONS_DELETE = "conversations.delete"

    # Phase 3 - Document Requests
    DOCUMENT_REQUESTS_READ = "document_requests.read"
    DOCUMENT_REQUESTS_CREATE = "document_requests.create"
    DOCUMENT_REQUESTS_UPDATE = "document_requests.update"
    DOCUMENT_REQUESTS_DELETE = "document_requests.delete"
    DOCUMENT_REQUESTS_SEND = "document_requests.send"

    # Phase 3 - Campaigns
    CAMPAIGNS_READ = "campaigns.read"
    CAMPAIGNS_CREATE = "campaigns.create"
    CAMPAIGNS_UPDATE = "campaigns.update"
    CAMPAIGNS_DELETE = "campaigns.delete"
    CAMPAIGNS_SEND = "campaigns.send"

    # Phase 3 - Templates
    TEMPLATES_READ = "templates.read"
    TEMPLATES_CREATE = "templates.create"
    TEMPLATES_UPDATE = "templates.update"
    TEMPLATES_DELETE = "templates.delete"

    # Phase 3 - Webhooks
    WEBHOOKS_READ = "webhooks.read"
    WEBHOOKS_CREATE = "webhooks.create"
    WEBHOOKS_UPDATE = "webhooks.update"
    WEBHOOKS_DELETE = "webhooks.delete"

    # Phase 3 - Events
    EVENTS_READ = "events.read"
    EVENTS_CREATE = "events.create"

    # Calendar
    CALENDAR_READ = "calendar.read"
    CALENDAR_CREATE = "calendar.create"
    CALENDAR_UPDATE = "calendar.update"
    CALENDAR_DELETE = "calendar.delete"

    # Phase 4 - Audit Workspace
    AUDIT_ENGAGEMENT_READ = "audit_engagement.read"
    AUDIT_ENGAGEMENT_CREATE = "audit_engagement.create"
    AUDIT_ENGAGEMENT_UPDATE = "audit_engagement.update"
    AUDIT_ENGAGEMENT_DELETE = "audit_engagement.delete"
    AUDIT_ENGAGEMENT_TRANSITION = "audit_engagement.transition"
    AUDIT_WORKING_PAPER_READ = "audit_working_paper.read"
    AUDIT_WORKING_PAPER_CREATE = "audit_working_paper.create"
    AUDIT_WORKING_PAPER_UPDATE = "audit_working_paper.update"
    AUDIT_WORKING_PAPER_DELETE = "audit_working_paper.delete"
    AUDIT_EVIDENCE_READ = "audit_evidence.read"
    AUDIT_EVIDENCE_CREATE = "audit_evidence.create"
    AUDIT_EVIDENCE_UPDATE = "audit_evidence.update"
    AUDIT_EVIDENCE_DELETE = "audit_evidence.delete"
    AUDIT_REVIEW_READ = "audit_review.read"
    AUDIT_REVIEW_CREATE = "audit_review.create"
    AUDIT_REVIEW_UPDATE = "audit_review.update"
    AUDIT_REVIEW_DELETE = "audit_review.delete"
    AUDIT_REVIEW_TRANSITION = "audit_review.transition"
    AUDIT_SIGN_OFF_READ = "audit_sign_off.read"
    AUDIT_SIGN_OFF_CREATE = "audit_sign_off.create"
    AUDIT_SIGN_OFF_UPDATE = "audit_sign_off.update"
    AUDIT_SIGN_OFF_DELETE = "audit_sign_off.delete"

    # Phase 4 - Attendance
    ATTENDANCE_READ = "attendance.read"
    ATTENDANCE_CREATE = "attendance.create"
    ATTENDANCE_UPDATE = "attendance.update"
    ATTENDANCE_DELETE = "attendance.delete"
    ATTENDANCE_APPROVE = "attendance.approve"

    # Phase 4 - Time Tracking
    TIME_ENTRY_READ = "time_entry.read"
    TIME_ENTRY_CREATE = "time_entry.create"
    TIME_ENTRY_UPDATE = "time_entry.update"
    TIME_ENTRY_DELETE = "time_entry.delete"
    TIME_ENTRY_APPROVE = "time_entry.approve"
    TIME_ENTRY_REPORT = "time_entry.report"

    # Phase 4 - Leave
    LEAVE_READ = "leave.read"
    LEAVE_CREATE = "leave.create"
    LEAVE_UPDATE = "leave.update"
    LEAVE_DELETE = "leave.delete"
    LEAVE_APPROVE = "leave.approve"
    LEAVE_BALANCE = "leave.balance"

    # Phase 4 - Physical Files
    PHYSICAL_FILE_READ = "physical_file.read"
    PHYSICAL_FILE_CREATE = "physical_file.create"
    PHYSICAL_FILE_UPDATE = "physical_file.update"
    PHYSICAL_FILE_DELETE = "physical_file.delete"
    PHYSICAL_FILE_CHECKOUT = "physical_file.checkout"
    PHYSICAL_FILE_CHECKIN = "physical_file.checkin"
    PHYSICAL_FILE_MOVE = "physical_file.move"

    # Phase 4 - Registers
    REGISTER_READ = "register.read"
    REGISTER_CREATE = "register.create"
    REGISTER_UPDATE = "register.update"
    REGISTER_DELETE = "register.delete"


class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    FIRM_ADMIN = "firm_admin"
    PARTNER = "partner"
    MANAGER = "manager"
    SENIOR_ASSOCIATE = "senior_associate"
    ASSOCIATE = "associate"
    JUNIOR_ASSOCIATE = "junior_associate"
    ADMIN_STAFF = "admin_staff"
    CLIENT_PORTAL = "client_portal"


@dataclass
class PermissionRegistry:
    role_permissions: dict[Role, set[Permission]] = field(default_factory=dict)

    def __post_init__(self):
        self._init_default_permissions()

    def _init_default_permissions(self) -> None:
        # Define base permissions for each role
        firm_admin_perms = {
            Permission.CLIENTS_READ, Permission.CLIENTS_CREATE, Permission.CLIENTS_UPDATE, Permission.CLIENTS_DELETE,
            Permission.MATTERS_READ, Permission.MATTERS_CREATE, Permission.MATTERS_UPDATE, Permission.MATTERS_DELETE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE, Permission.TASKS_DELETE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD, Permission.DOCUMENTS_DELETE,
            Permission.BILLING_READ, Permission.BILLING_MANAGE,
            Permission.COMPLIANCE_READ, Permission.COMPLIANCE_CREATE, Permission.COMPLIANCE_UPDATE, Permission.COMPLIANCE_DELETE,
            Permission.ADMIN_USERS_MANAGE, Permission.ADMIN_ROLES_MANAGE, Permission.ADMIN_FIRM_MANAGE,
            Permission.AUDIT_READ, Permission.AUDIT_MANAGE,
            # Phase 2
            Permission.WORKFLOW_READ, Permission.WORKFLOW_CREATE, Permission.WORKFLOW_UPDATE, Permission.WORKFLOW_DELETE, Permission.WORKFLOW_TRANSITION,
            Permission.REVIEWS_READ, Permission.REVIEWS_CREATE, Permission.REVIEWS_UPDATE, Permission.REVIEWS_DELETE, Permission.REVIEWS_TRANSITION, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ, Permission.TDS_CREATE, Permission.TDS_UPDATE, Permission.TDS_DELETE, Permission.TDS_TRANSITION,
            Permission.MCA_ROC_READ, Permission.MCA_ROC_CREATE, Permission.MCA_ROC_UPDATE, Permission.MCA_ROC_DELETE, Permission.MCA_ROC_TRANSITION,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE, Permission.NOTICES_DELETE, Permission.NOTICES_TRANSITION, Permission.NOTICES_ESCALATE,
            Permission.WORKLOAD_READ, Permission.WORKLOAD_UPDATE,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_CREATE, Permission.ASSIGNMENTS_UPDATE, Permission.ASSIGNMENTS_REASSIGN, Permission.ASSIGNMENTS_ESCALATE,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ, Permission.NOTIFICATIONS_CREATE, Permission.NOTIFICATIONS_UPDATE, Permission.NOTIFICATIONS_DELETE,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_DELETE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE, Permission.CONVERSATIONS_DELETE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_DELETE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE, Permission.CAMPAIGNS_UPDATE, Permission.CAMPAIGNS_DELETE, Permission.CAMPAIGNS_SEND,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE, Permission.TEMPLATES_UPDATE, Permission.TEMPLATES_DELETE,
            Permission.WEBHOOKS_READ, Permission.WEBHOOKS_CREATE, Permission.WEBHOOKS_UPDATE, Permission.WEBHOOKS_DELETE,
            Permission.EVENTS_READ, Permission.EVENTS_CREATE,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE, Permission.CALENDAR_UPDATE, Permission.CALENDAR_DELETE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_DELETE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
            Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
            Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_DELETE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_DELETE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_DELETE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_DELETE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_DELETE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        partner_perms = {
            Permission.CLIENTS_READ, Permission.CLIENTS_CREATE, Permission.CLIENTS_UPDATE,
            Permission.MATTERS_READ, Permission.MATTERS_CREATE, Permission.MATTERS_UPDATE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.BILLING_READ, Permission.BILLING_MANAGE,
            Permission.COMPLIANCE_READ, Permission.COMPLIANCE_CREATE, Permission.COMPLIANCE_UPDATE,
            Permission.AUDIT_READ, Permission.AUDIT_MANAGE,
            # Phase 2
            Permission.WORKFLOW_READ, Permission.WORKFLOW_CREATE, Permission.WORKFLOW_UPDATE, Permission.WORKFLOW_TRANSITION,
            Permission.REVIEWS_READ, Permission.REVIEWS_CREATE, Permission.REVIEWS_UPDATE, Permission.REVIEWS_TRANSITION, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ, Permission.TDS_CREATE, Permission.TDS_UPDATE, Permission.TDS_TRANSITION,
            Permission.MCA_ROC_READ, Permission.MCA_ROC_CREATE, Permission.MCA_ROC_UPDATE, Permission.MCA_ROC_TRANSITION,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE, Permission.NOTICES_TRANSITION, Permission.NOTICES_ESCALATE,
            Permission.WORKLOAD_READ, Permission.WORKLOAD_UPDATE,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_CREATE, Permission.ASSIGNMENTS_UPDATE, Permission.ASSIGNMENTS_REASSIGN, Permission.ASSIGNMENTS_ESCALATE,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ, Permission.NOTIFICATIONS_CREATE, Permission.NOTIFICATIONS_UPDATE,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_DELETE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE, Permission.CONVERSATIONS_DELETE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_DELETE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE, Permission.CAMPAIGNS_UPDATE, Permission.CAMPAIGNS_DELETE, Permission.CAMPAIGNS_SEND,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE, Permission.TEMPLATES_UPDATE, Permission.TEMPLATES_DELETE,
            Permission.WEBHOOKS_READ, Permission.WEBHOOKS_CREATE, Permission.WEBHOOKS_UPDATE, Permission.WEBHOOKS_DELETE,
            Permission.EVENTS_READ, Permission.EVENTS_CREATE,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE, Permission.CALENDAR_UPDATE, Permission.CALENDAR_DELETE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_DELETE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
            Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
            Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_DELETE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_DELETE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_DELETE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_DELETE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_DELETE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        manager_perms = {
            Permission.CLIENTS_READ, Permission.CLIENTS_CREATE, Permission.CLIENTS_UPDATE,
            Permission.MATTERS_READ, Permission.MATTERS_CREATE, Permission.MATTERS_UPDATE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.BILLING_READ,
            Permission.COMPLIANCE_READ, Permission.COMPLIANCE_CREATE, Permission.COMPLIANCE_UPDATE,
            # Phase 2
            Permission.WORKFLOW_READ, Permission.WORKFLOW_CREATE, Permission.WORKFLOW_UPDATE, Permission.WORKFLOW_TRANSITION,
            Permission.REVIEWS_READ, Permission.REVIEWS_CREATE, Permission.REVIEWS_UPDATE, Permission.REVIEWS_TRANSITION, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ, Permission.TDS_CREATE, Permission.TDS_UPDATE, Permission.TDS_TRANSITION,
            Permission.MCA_ROC_READ, Permission.MCA_ROC_CREATE, Permission.MCA_ROC_UPDATE, Permission.MCA_ROC_TRANSITION,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE, Permission.NOTICES_TRANSITION, Permission.NOTICES_ESCALATE,
            Permission.WORKLOAD_READ, Permission.WORKLOAD_UPDATE,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_CREATE, Permission.ASSIGNMENTS_UPDATE, Permission.ASSIGNMENTS_REASSIGN,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ, Permission.NOTIFICATIONS_CREATE, Permission.NOTIFICATIONS_UPDATE,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_DELETE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE, Permission.CONVERSATIONS_DELETE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_DELETE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE, Permission.CAMPAIGNS_UPDATE, Permission.CAMPAIGNS_DELETE, Permission.CAMPAIGNS_SEND,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE, Permission.TEMPLATES_UPDATE, Permission.TEMPLATES_DELETE,
            Permission.WEBHOOKS_READ, Permission.WEBHOOKS_CREATE, Permission.WEBHOOKS_UPDATE, Permission.WEBHOOKS_DELETE,
            Permission.EVENTS_READ, Permission.EVENTS_CREATE,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE, Permission.CALENDAR_UPDATE, Permission.CALENDAR_DELETE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_DELETE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
            Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
            Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_DELETE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE, Permission.AUDIT_SIGN_OFF_UPDATE, Permission.AUDIT_SIGN_OFF_DELETE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_DELETE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_DELETE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_DELETE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_DELETE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        senior_associate_perms = {
            Permission.CLIENTS_READ, Permission.CLIENTS_CREATE, Permission.CLIENTS_UPDATE,
            Permission.MATTERS_READ, Permission.MATTERS_CREATE, Permission.MATTERS_UPDATE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.COMPLIANCE_READ, Permission.COMPLIANCE_CREATE, Permission.COMPLIANCE_UPDATE,
            # Phase 2
            Permission.WORKFLOW_READ, Permission.WORKFLOW_TRANSITION,
            Permission.REVIEWS_READ, Permission.REVIEWS_CREATE, Permission.REVIEWS_UPDATE, Permission.REVIEWS_TRANSITION, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ, Permission.TDS_CREATE, Permission.TDS_UPDATE, Permission.TDS_TRANSITION,
            Permission.MCA_ROC_READ, Permission.MCA_ROC_CREATE, Permission.MCA_ROC_UPDATE, Permission.MCA_ROC_TRANSITION,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE, Permission.NOTICES_TRANSITION,
            Permission.WORKLOAD_READ,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_UPDATE,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ, Permission.NOTIFICATIONS_CREATE,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE, Permission.CAMPAIGNS_UPDATE,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE, Permission.TEMPLATES_UPDATE,
            Permission.WEBHOOKS_READ,
            Permission.EVENTS_READ,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE, Permission.CALENDAR_UPDATE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
            Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
            Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE, Permission.AUDIT_SIGN_OFF_UPDATE, Permission.AUDIT_SIGN_OFF_DELETE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        associate_perms = {
            Permission.CLIENTS_READ,
            Permission.MATTERS_READ, Permission.MATTERS_CREATE, Permission.MATTERS_UPDATE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.COMPLIANCE_READ, Permission.COMPLIANCE_CREATE,
            # Phase 2
            Permission.WORKFLOW_READ, Permission.WORKFLOW_TRANSITION,
            Permission.REVIEWS_READ, Permission.REVIEWS_CREATE, Permission.REVIEWS_UPDATE, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ, Permission.TDS_CREATE, Permission.TDS_UPDATE,
            Permission.MCA_ROC_READ, Permission.MCA_ROC_CREATE, Permission.MCA_ROC_UPDATE,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE,
            Permission.WORKLOAD_READ,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_UPDATE,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE,
            Permission.WEBHOOKS_READ,
            Permission.EVENTS_READ,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
            Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
            Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE, Permission.AUDIT_SIGN_OFF_UPDATE, Permission.AUDIT_SIGN_OFF_DELETE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        junior_associate_perms = {
            Permission.CLIENTS_READ,
            Permission.MATTERS_READ,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.COMPLIANCE_READ,
            # Phase 2
            Permission.WORKFLOW_READ,
            Permission.REVIEWS_READ, Permission.REVIEWS_COMMENT,
            Permission.TDS_READ,
            Permission.MCA_ROC_READ,
            Permission.NOTICES_READ,
            Permission.WORKLOAD_READ,
            Permission.ASSIGNMENTS_READ,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE,
            Permission.CONVERSATIONS_READ,
            Permission.DOCUMENT_REQUESTS_READ,
            Permission.CAMPAIGNS_READ,
            Permission.TEMPLATES_READ,
            Permission.WEBHOOKS_READ,
            Permission.EVENTS_READ,
            # Calendar
            Permission.CALENDAR_READ,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ,
            Permission.AUDIT_WORKING_PAPER_READ,
            Permission.AUDIT_EVIDENCE_READ,
            Permission.AUDIT_REVIEW_READ,
            Permission.AUDIT_SIGN_OFF_READ,
            Permission.ATTENDANCE_READ,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ,
            Permission.PHYSICAL_FILE_READ,
            Permission.REGISTER_READ,
        }

        admin_staff_perms = {
            Permission.CLIENTS_READ, Permission.CLIENTS_CREATE, Permission.CLIENTS_UPDATE,
            Permission.TASKS_READ, Permission.TASKS_CREATE, Permission.TASKS_UPDATE,
            Permission.DOCUMENTS_READ, Permission.DOCUMENTS_UPLOAD,
            Permission.BILLING_READ,
            # Phase 2
            Permission.WORKFLOW_READ,
            Permission.REVIEWS_READ,
            Permission.TDS_READ,
            Permission.MCA_ROC_READ,
            Permission.NOTICES_READ, Permission.NOTICES_CREATE, Permission.NOTICES_UPDATE,
            Permission.WORKLOAD_READ,
            Permission.ASSIGNMENTS_READ, Permission.ASSIGNMENTS_UPDATE,
            Permission.COLLABORATION_READ, Permission.COLLABORATION_COMMENT,
            Permission.NOTIFICATIONS_READ, Permission.NOTIFICATIONS_CREATE,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE, Permission.COMMUNICATIONS_UPDATE, Permission.COMMUNICATIONS_SEND,
            Permission.CONVERSATIONS_READ, Permission.CONVERSATIONS_CREATE, Permission.CONVERSATIONS_UPDATE,
            Permission.DOCUMENT_REQUESTS_READ, Permission.DOCUMENT_REQUESTS_CREATE, Permission.DOCUMENT_REQUESTS_UPDATE, Permission.DOCUMENT_REQUESTS_SEND,
            Permission.CAMPAIGNS_READ, Permission.CAMPAIGNS_CREATE, Permission.CAMPAIGNS_UPDATE,
            Permission.TEMPLATES_READ, Permission.TEMPLATES_CREATE, Permission.TEMPLATES_UPDATE,
            Permission.WEBHOOKS_READ, Permission.WEBHOOKS_CREATE, Permission.WEBHOOKS_UPDATE,
            Permission.EVENTS_READ, Permission.EVENTS_CREATE,
            # Calendar
            Permission.CALENDAR_READ, Permission.CALENDAR_CREATE, Permission.CALENDAR_UPDATE,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ, Permission.AUDIT_ENGAGEMENT_CREATE, Permission.AUDIT_ENGAGEMENT_UPDATE, Permission.AUDIT_ENGAGEMENT_TRANSITION,
            Permission.AUDIT_WORKING_PAPER_READ, Permission.AUDIT_WORKING_PAPER_CREATE, Permission.AUDIT_WORKING_PAPER_UPDATE, Permission.AUDIT_WORKING_PAPER_DELETE,
Permission.AUDIT_EVIDENCE_READ, Permission.AUDIT_EVIDENCE_CREATE, Permission.AUDIT_EVIDENCE_UPDATE, Permission.AUDIT_EVIDENCE_DELETE,
Permission.AUDIT_REVIEW_READ, Permission.AUDIT_REVIEW_CREATE, Permission.AUDIT_REVIEW_UPDATE, Permission.AUDIT_REVIEW_DELETE, Permission.AUDIT_REVIEW_TRANSITION,
            Permission.AUDIT_SIGN_OFF_READ, Permission.AUDIT_SIGN_OFF_CREATE, Permission.AUDIT_SIGN_OFF_UPDATE, Permission.AUDIT_SIGN_OFF_DELETE,
            Permission.ATTENDANCE_READ, Permission.ATTENDANCE_CREATE, Permission.ATTENDANCE_UPDATE, Permission.ATTENDANCE_DELETE, Permission.ATTENDANCE_APPROVE,
            Permission.TIME_ENTRY_READ, Permission.TIME_ENTRY_CREATE, Permission.TIME_ENTRY_UPDATE, Permission.TIME_ENTRY_DELETE, Permission.TIME_ENTRY_APPROVE, Permission.TIME_ENTRY_REPORT,
            Permission.LEAVE_READ, Permission.LEAVE_CREATE, Permission.LEAVE_UPDATE, Permission.LEAVE_DELETE, Permission.LEAVE_APPROVE, Permission.LEAVE_BALANCE,
            Permission.PHYSICAL_FILE_READ, Permission.PHYSICAL_FILE_CREATE, Permission.PHYSICAL_FILE_UPDATE, Permission.PHYSICAL_FILE_DELETE, Permission.PHYSICAL_FILE_CHECKOUT, Permission.PHYSICAL_FILE_CHECKIN, Permission.PHYSICAL_FILE_MOVE,
            Permission.REGISTER_READ, Permission.REGISTER_CREATE, Permission.REGISTER_UPDATE, Permission.REGISTER_DELETE,
        }

        client_portal_perms = {
            Permission.CLIENTS_READ,
            Permission.DOCUMENTS_READ,
            # Phase 2
            Permission.NOTIFICATIONS_READ,
            # Phase 3
            Permission.COMMUNICATIONS_READ, Permission.COMMUNICATIONS_CREATE,
            Permission.CONVERSATIONS_READ,
            Permission.DOCUMENT_REQUESTS_READ,
            # Calendar
            Permission.CALENDAR_READ,
            # Phase 4
            Permission.AUDIT_ENGAGEMENT_READ,
            Permission.AUDIT_WORKING_PAPER_READ,
            Permission.AUDIT_EVIDENCE_READ,
            Permission.AUDIT_REVIEW_READ,
            Permission.AUDIT_SIGN_OFF_READ,
            Permission.ATTENDANCE_READ,
            Permission.TIME_ENTRY_READ,
            Permission.LEAVE_READ,
            Permission.PHYSICAL_FILE_READ,
            Permission.REGISTER_READ,
        }

        self.role_permissions = {
            Role.SUPER_ADMIN: {p for p in Permission},
            Role.FIRM_ADMIN: firm_admin_perms,
            Role.PARTNER: partner_perms,
            Role.MANAGER: manager_perms,
            Role.SENIOR_ASSOCIATE: senior_associate_perms,
            Role.ASSOCIATE: associate_perms,
            Role.JUNIOR_ASSOCIATE: junior_associate_perms,
            Role.ADMIN_STAFF: admin_staff_perms,
            Role.CLIENT_PORTAL: client_portal_perms,
        }

    def get_permissions_for_role(self, role: Role) -> set[Permission]:
        return self.role_permissions.get(role, set())

    def role_has_permission(self, role: Role, permission: Permission) -> bool:
        return permission in self.get_permissions_for_role(role)

    def get_all_permissions(self) -> list[Permission]:
        return list(Permission)

    def get_all_roles(self) -> list[Role]:
        return list(Role)


_permission_registry: PermissionRegistry = None


def get_permission_registry() -> PermissionRegistry:
    global _permission_registry
    if _permission_registry is None:
        _permission_registry = PermissionRegistry()
    return _permission_registry
