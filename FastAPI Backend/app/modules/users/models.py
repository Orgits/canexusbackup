import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Boolean, Text, DateTime, ForeignKey, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.firms.models import Firm
    from app.modules.users.models import Team


class User(Base, TenantBaseModelMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roles: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    direct_permissions: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    date_of_joining: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", back_populates="users", lazy="selectin")
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="members", lazy="selectin")

    def get_all_permissions(self) -> List[str]:
        from app.core.permissions.registry import get_permission_registry, Role
        registry = get_permission_registry()
        permissions = set(self.direct_permissions)
        for role_str in self.roles:
            try:
                role = Role(role_str)
                permissions.update(p.value for p in registry.get_permissions_for_role(role))
            except ValueError:
                continue
        return list(permissions)

    def has_permission(self, permission: str) -> bool:
        return permission in self.get_all_permissions()

    def has_role(self, role: str) -> bool:
        return role in self.roles


class Team(Base, TenantBaseModelMixin):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    specialization: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", back_populates="branches", lazy="selectin")
    lead: Mapped[Optional["User"]] = relationship("User", foreign_keys=[lead_id], lazy="selectin")
    members: Mapped[List["User"]] = relationship("User", back_populates="team", lazy="dynamic")