from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import get_async_db
from app.core.security.jwt import TokenType, decode_token
from app.core.tenancy.context import TenantContext, clear_tenant_context, set_tenant_context
from app.modules.firms.models import Firm
from app.modules.users.models import User


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith("/api/v1/auth") or request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        # Extract token from Authorization header manually
        auth_header = request.headers.get("Authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]

        try:
            async for db in get_async_db():
                if token:
                    payload = decode_token(token)
                    if payload and payload.type == TokenType.ACCESS:
                        try:
                            user_id = UUID(payload.sub)
                        except ValueError:
                            user_id = None
                        
                        if user_id:
                            result = await db.execute(select(User).where(User.id == user_id))
                            user = result.scalar_one_or_none()
                            if user and user.is_active:
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
