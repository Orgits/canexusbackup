import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from enum import Enum as PyEnum
from sqlalchemy import (
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    func,
    Enum,
    ARRAY,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database.base import Base, TenantBaseModelMixin

if TYPE_CHECKING:
    from app.modules.users.models import User, Team
    from app.modules.matters.models import Matter
    from app.modules.tasks.models import Task
    from app.modules.documents.models import Document
    from app.modules.compliance.models import ComplianceCycle


class ClientCategory(str, PyEnum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    LLP = "llp"
    PARTNERSHIP = "partnership"
    HUF = "huf"
    TRUST = "trust"
    AOP = "aop"
    BOI = "boi"
    GOVERNMENT = "government"
    NON_PROFIT = "non_profit"
    FOREIGN = "foreign"
    OTHER = "other"


class ClientStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"
    ONBOARDING = "onboarding"
    PROSPECT = "prospect"


class Client(Base, TenantBaseModelMixin):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_tenant_name", "tenant_id", "name"),
        Index("ix_clients_tenant_pan", "tenant_id", "pan"),
        Index("ix_clients_tenant_gstin", "tenant_id", "gstin"),
        Index("ix_clients_tenant_status", "tenant_id", "status"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[ClientCategory] = mapped_column(Enum(ClientCategory), default=ClientCategory.INDIVIDUAL, nullable=False)
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.ACTIVE, nullable=False)

    pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, index=True)
    tan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cin: Mapped[Optional[str]] = mapped_column(String(21), nullable=True)
    din: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    aadhaar: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    passport: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    other_ids: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India", nullable=False)

    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    responsible_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responsible_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tenant: Mapped["Firm"] = relationship("Firm", back_populates="clients", lazy="selectin")
    responsible_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[responsible_user_id], lazy="selectin")
    responsible_team: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[responsible_team_id], lazy="selectin")
    contacts: Mapped[List["ClientContact"]] = relationship("ClientContact", back_populates="client", lazy="dynamic", cascade="all, delete-orphan")
    services: Mapped[List["ClientService"]] = relationship("ClientService", back_populates="client", lazy="dynamic", cascade="all, delete-orphan")
    matters: Mapped[List["Matter"]] = relationship("Matter", back_populates="client", lazy="dynamic")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="client", lazy="dynamic")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="client", lazy="dynamic")
    compliance_cycles: Mapped[List["ComplianceCycle"]] = relationship("ComplianceCycle", back_populates="client", lazy="dynamic")


class ClientContact(Base, TenantBaseModelMixin):
    __tablename__ = "client_contacts"
    __table_args__ = (
        Index("ix_client_contacts_tenant_client", "tenant_id", "client_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    designation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="contacts", lazy="selectin")


class ClientService(Base, TenantBaseModelMixin):
    __tablename__ = "client_services"
    __table_args__ = (
        Index("ix_client_services_tenant_client", "tenant_id", "client_id"),
        UniqueConstraint("client_id", "service_type", name="uq_client_service_type"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    service_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_frequency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    billing_amount: Mapped[Optional[float]] = mapped_column(nullable=True)
    responsible_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    responsible_team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
    )
    extra_metadata: Mapped[dict] = mapped_column(JSONB, default=lambda: {}, nullable=False)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("firms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    client: Mapped["Client"] = relationship("Client", back_populates="services", lazy="selectin")