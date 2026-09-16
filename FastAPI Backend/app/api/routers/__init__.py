from fastapi import APIRouter

from app.core.config import get_settings
from app.modules.assignments.router import router as assignments_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.billing.router import router as billing_router
from app.modules.calendar.router import router as calendar_router
from app.modules.channels.router import router as channels_router
from app.modules.clients.router import router as clients_router
from app.modules.collaboration.router import router as collaboration_router
from app.modules.compliance.router import router as compliance_router
from app.modules.communications.router import router as communications_router
from app.modules.consent.router import router as consent_router
from app.modules.documents.router import router as documents_router
from app.modules.firms.router import router as firms_router
from app.modules.matters.router import router as matters_router
from app.modules.mca_roc.router import router as mca_roc_router
from app.modules.notices.router import router as notices_router
from app.modules.notifications.router import router as notifications_router
from app.modules.reviews.router import router as reviews_router
from app.modules.tasks.router import router as tasks_router
from app.modules.tds.router import router as tds_router
from app.modules.users.router import router as users_router
from app.modules.workflow.router import router as workflow_router
from app.modules.workload.router import router as workload_router

# Phase 3 modules
from app.modules.campaigns.router import router as campaigns_router
from app.modules.conversations.router import router as conversations_router
from app.modules.templates.router import router as templates_router
from app.modules.consent.router import router as consent_router
from app.modules.suppression.router import router as suppression_router
from app.modules.document_requests.router import router as document_requests_router
from app.modules.webhooks.router import router as webhooks_router
from app.modules.channels.router import router as channels_router
from app.modules.ocr.router import router as ocr_router
from app.modules.ai_processing.router import router as ai_processing_router
from app.modules.suppression.router import router as suppression_router
from app.modules.document_requests.router import router as document_requests_router

settings = get_settings()

api_router = APIRouter(prefix=f"/{settings.API_VERSION}")

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(firms_router, prefix="/firms", tags=["Firms"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(clients_router, prefix="/clients", tags=["Clients"])
api_router.include_router(matters_router, prefix="/matters", tags=["Matters"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(compliance_router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(billing_router, prefix="/billing", tags=["Billing"])
api_router.include_router(calendar_router, prefix="/calendar", tags=["Calendar"])
api_router.include_router(audit_router, prefix="/audit", tags=["Audit"])
api_router.include_router(workflow_router, prefix="/workflow", tags=["Workflow Engine"])
api_router.include_router(reviews_router, prefix="/reviews", tags=["Review & Approval Engine"])
api_router.include_router(tds_router, prefix="/tds", tags=["TDS Compliance"])
api_router.include_router(mca_roc_router, prefix="/mca-roc", tags=["MCA/ROC Compliance"])
api_router.include_router(notices_router, prefix="/notices", tags=["Notice Management"])
api_router.include_router(workload_router, prefix="/workload", tags=["Workload & Capacity"])
api_router.include_router(assignments_router, prefix="/assignments", tags=["Assignment & Escalation"])
api_router.include_router(collaboration_router, prefix="/collaboration", tags=["Collaboration & Comments"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])

# Phase 3 routers
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["Campaigns"])
api_router.include_router(conversations_router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(templates_router, prefix="/templates", tags=["Templates"])
api_router.include_router(consent_router, prefix="/consent", tags=["Consent"])
api_router.include_router(suppression_router, prefix="/suppression", tags=["Suppression"])
api_router.include_router(document_requests_router, prefix="/document-requests", tags=["Document Requests"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(channels_router, prefix="/channels", tags=["Channel Integrations"])
api_router.include_router(ocr_router, prefix="/ocr", tags=["OCR"])
api_router.include_router(ai_processing_router, prefix="/ai", tags=["AI Processing"])
api_router.include_router(suppression_router, prefix="/suppression", tags=["Suppression"])
api_router.include_router(document_requests_router, prefix="/document-requests", tags=["Document Requests"])
