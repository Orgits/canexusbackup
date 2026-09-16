from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.security.dependencies import get_current_user
from app.core.tenancy.context import TenantContext, set_tenant_context

if TYPE_CHECKING:
    from app.modules.firms.models import Firm
    from app.modules.users.models import User

async def get_current_tenant(
    current_user: "User" = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> "Firm":
    from app.modules.firms.models import Firm
    result = await db.execute(select(Firm).where(Firm.id == current_user.tenant_id))
    firm = result.scalar_one_or_none()
    if not firm:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant not found",
        )
    if not firm.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )
    return firm


async def require_tenant_access(
    tenant_id: UUID,
    current_user: "User" = Depends(get_current_user),
) -> None:
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )


async def setup_tenant_context(
    current_user: "User" = Depends(get_current_user),
    current_tenant: "Firm" = Depends(get_current_tenant),
) -> TenantContext:
    context = TenantContext(
        tenant_id=current_tenant.id,
        firm=current_tenant,
        user_id=current_user.id,
    )
    set_tenant_context(context)
    return context
