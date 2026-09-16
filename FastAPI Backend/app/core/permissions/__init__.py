from .dependencies import require_all_permissions, require_any_permission, require_permission, require_role
from .registry import Permission, PermissionRegistry, Role, get_permission_registry

__all__ = [
    "Permission",
    "PermissionRegistry",
    "Role",
    "get_permission_registry",
    "require_all_permissions",
    "require_any_permission",
    "require_permission",
    "require_role",
]
