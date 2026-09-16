from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status

from app.core.permissions.registry import Permission, Role, get_permission_registry
from app.core.security.dependencies import get_current_user

if TYPE_CHECKING:
    from app.modules.users.models import User


def require_permission(permission: Permission):
    async def permission_checker(current_user: "User" = Depends(get_current_user)) -> "User":
        registry = get_permission_registry()
        user_roles = [Role(r) for r in current_user.roles if r in [r.value for r in Role]]
        has_permission = any(
            registry.role_has_permission(role, permission) for role in user_roles
        ) or any(
            p == permission.value for p in current_user.direct_permissions
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return current_user

    return permission_checker


def require_role(role: Role):
    async def role_checker(current_user: "User" = Depends(get_current_user)) -> "User":
        user_roles = [Role(r) for r in current_user.roles if r in [r.value for r in Role]]
        if role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}",
            )
        return current_user

    return role_checker


def require_any_permission(permissions: list[Permission]):
    async def permission_checker(current_user: "User" = Depends(get_current_user)) -> "User":
        registry = get_permission_registry()
        user_roles = [Role(r) for r in current_user.roles if r in [r.value for r in Role]]
        has_permission = any(
            any(registry.role_has_permission(role, p) for role in user_roles)
            or any(p.value == dp for dp in current_user.direct_permissions)
            for p in permissions
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {[p.value for p in permissions]}",
            )
        return current_user

    return permission_checker


def require_all_permissions(permissions: list[Permission]):
    async def permission_checker(current_user: "User" = Depends(get_current_user)) -> "User":
        registry = get_permission_registry()
        user_roles = [Role(r) for r in current_user.roles if r in [r.value for r in Role]]
        for permission in permissions:
            has_permission = any(
                registry.role_has_permission(role, permission) for role in user_roles
            ) or any(permission.value == dp for dp in current_user.direct_permissions)
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
        return current_user

    return permission_checker
