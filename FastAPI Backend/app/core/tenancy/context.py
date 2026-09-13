from contextvars import ContextVar
from typing import Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.modules.firms.models import Firm

tenant_context: ContextVar[Optional["TenantContext"]] = ContextVar("tenant_context", default=None)


class TenantContext:
    def __init__(
        self,
        tenant_id: UUID,
        firm: "Firm",
        user_id: UUID,
    ):
        self.tenant_id = tenant_id
        self.firm = firm
        self.user_id = user_id

    def __repr__(self) -> str:
        return f"TenantContext(tenant_id={self.tenant_id}, user_id={self.user_id})"


def get_tenant_context() -> Optional[TenantContext]:
    return tenant_context.get()


def set_tenant_context(context: TenantContext) -> None:
    tenant_context.set(context)


def clear_tenant_context() -> None:
    tenant_context.set(None)