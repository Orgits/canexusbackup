from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import get_async_db
from app.core.security.dependencies import get_optional_user
from app.core.tenancy.context import TenantContext, clear_tenant_context, set_tenant_context
from app.modules.firms.models import Firm


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/v1/auth") or request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        try:
            async for db in get_async_db():
                user = await get_optional_user(request, db)
                if user:
                    result = await db.execute(
                        select(Firm).where(Firm.id == user.tenant_id)
                    )
                    firm = result.scalar_one_or_none()
                    if firm and firm.is_active:
                        context = TenantContext(
                            tenant_id=firm.id,
                            firm=firm,
                            user_id=user.id,
                        )
                        set_tenant_context(context)

                response = await call_next(request)
                return response
        finally:
            clear_tenant_context()
