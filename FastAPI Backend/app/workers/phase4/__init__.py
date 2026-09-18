# Phase 4 Celery Workers
# This module registers all Phase 4 workers with the Celery app

# Import to register workers
from app.workers.phase4 import dsc_worker  # noqa: F401
from app.workers.phase4 import udin_worker  # noqa: F401
from app.workers.phase4 import license_worker  # noqa: F401
from app.workers.phase4 import engagement_document_worker  # noqa: F401
from app.workers.phase4 import e_signature_worker  # noqa: F401
from app.workers.phase4 import mfa_worker  # noqa: F401

__all__ = []