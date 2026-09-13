from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.compliance.models import ComplianceType, ComplianceCycle, ComplianceApplicability, ComplianceStatus, ComplianceFrequency
from app.modules.compliance.schemas import (
    ComplianceTypeCreate,
    ComplianceTypeUpdate,
    ComplianceCycleCreate,
    ComplianceCycleUpdate,
    ComplianceApplicabilityCreate,
    ComplianceApplicabilityUpdate,
)
from app.modules.compliance.repository import ComplianceRepository
from app.modules.clients.models import Client


class ComplianceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = ComplianceRepository(db)

    async def create_type(self, data: ComplianceTypeCreate, tenant_id: UUID, created_by: UUID) -> ComplianceType:
        existing = await self.repository.get_type_by_code(data.code, tenant_id)
        if existing:
            raise ConflictException(detail="Compliance type with this code already exists")

        compliance_type = ComplianceType(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_type(compliance_type)

    async def get_type_by_id(self, type_id: UUID, tenant_id: UUID) -> ComplianceType:
        compliance_type = await self.repository.get_type_by_id(type_id, tenant_id)
        if not compliance_type:
            raise NotFoundException(detail="Compliance type not found")
        return compliance_type

    async def get_all_types(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[ComplianceType], int]:
        return await self.repository.get_all_types(tenant_id, page, page_size, search, category, is_active)

    async def update_type(self, type_id: UUID, tenant_id: UUID, data: ComplianceTypeUpdate, updated_by: UUID) -> ComplianceType:
        compliance_type = await self.get_type_by_id(type_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data:
            existing = await self.repository.get_type_by_code(update_data["code"], tenant_id)
            if existing and existing.id != type_id:
                raise ConflictException(detail="Compliance type with this code already exists")

        for field, value in update_data.items():
            setattr(compliance_type, field, value)
        compliance_type.updated_by = updated_by
        return await self.repository.update_type(compliance_type)

    async def delete_type(self, type_id: UUID, tenant_id: UUID) -> None:
        compliance_type = await self.get_type_by_id(type_id, tenant_id)
        if compliance_type.is_system:
            raise ConflictException(detail="Cannot delete system compliance type")
        await self.repository.delete_type(compliance_type)

    async def create_cycle(self, data: ComplianceCycleCreate, tenant_id: UUID, created_by: UUID) -> ComplianceCycle:
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        cycle = ComplianceCycle(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
            status=ComplianceStatus.PENDING,
        )
        return await self.repository.create_cycle(cycle)

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> ComplianceCycle:
        cycle = await self.repository.get_cycle_by_id(cycle_id, tenant_id)
        if not cycle:
            raise NotFoundException(detail="Compliance cycle not found")
        return cycle

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        compliance_type_id: Optional[UUID] = None,
        status: Optional[ComplianceStatus] = None,
        matter_id: Optional[UUID] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None,
        assigned_user_id: Optional[UUID] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[ComplianceCycle], int]:
        return await self.repository.get_all_cycles(
            tenant_id, page, page_size, search, client_id, compliance_type_id,
            status, matter_id, due_date_from, due_date_to, period_start, period_end,
            assigned_user_id, sort_by, sort_order
        )

    async def update_cycle(self, cycle_id: UUID, tenant_id: UUID, data: ComplianceCycleUpdate, updated_by: UUID) -> ComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(cycle, field, value)
        cycle.updated_by = updated_by
        return await self.repository.update_cycle(cycle)

    async def delete_cycle(self, cycle_id: UUID, tenant_id: UUID) -> None:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        await self.repository.delete_cycle(cycle)

    async def create_applicability(self, data: ComplianceApplicabilityCreate, tenant_id: UUID, created_by: UUID) -> ComplianceApplicability:
        existing = await self.repository.get_applicability(data.client_id, data.compliance_type_id, tenant_id)
        if existing:
            raise ConflictException(detail="Applicability record already exists")

        applicability = ComplianceApplicability(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_applicability(applicability)

    async def get_applicability(self, client_id: UUID, compliance_type_id: UUID, tenant_id: UUID) -> ComplianceApplicability:
        applicability = await self.repository.get_applicability(client_id, compliance_type_id, tenant_id)
        if not applicability:
            raise NotFoundException(detail="Applicability record not found")
        return applicability

    async def get_all_applicability(
        self,
        tenant_id: UUID,
        client_id: Optional[UUID] = None,
        compliance_type_id: Optional[UUID] = None,
    ) -> List[ComplianceApplicability]:
        return await self.repository.get_all_applicability(tenant_id, client_id, compliance_type_id)

    async def update_applicability(
        self,
        client_id: UUID,
        compliance_type_id: UUID,
        tenant_id: UUID,
        data: ComplianceApplicabilityUpdate,
        updated_by: UUID,
    ) -> ComplianceApplicability:
        applicability = await self.get_applicability(client_id, compliance_type_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(applicability, field, value)
        applicability.updated_by = updated_by
        return await self.repository.update_applicability(applicability)

    async def delete_applicability(self, client_id: UUID, compliance_type_id: UUID, tenant_id: UUID) -> None:
        applicability = await self.get_applicability(client_id, compliance_type_id, tenant_id)
        await self.repository.delete_applicability(applicability)

    async def initialize_system_types(self, tenant_id: UUID) -> List[ComplianceType]:
        system_types = [
            {
                "code": "ITR",
                "name": "Income Tax Return",
                "description": "Annual income tax return filing",
                "category": "Direct Tax",
                "frequency": ComplianceFrequency.ANNUAL,
                "applicability_rules": {"entity_types": ["individual", "company", "llp", "partnership", "huf", "trust", "aop"]},
                "due_date_rules": {"rule": "31st July of assessment year", "extension_rule": "CBDT notification"},
                "period_rules": {"financial_year": "April to March"},
                "default_checklist": [
                    {"item": "Form 16/16A collection", "mandatory": True},
                    {"item": "Bank statements", "mandatory": True},
                    {"item": "Investment proofs", "mandatory": True},
                    {"item": "TDS certificates", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "Form 16", "mandatory": True},
                    {"document": "Form 26AS", "mandatory": True},
                    {"document": "AIS/TIS", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Collection", "order": 1},
                    {"stage": "Computation", "order": 2},
                    {"stage": "Review", "order": 3},
                    {"stage": "Filing", "order": 4},
                ],
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "GST",
                "name": "GST Return Filing",
                "description": "Monthly/Quarterly/Annual GST return filing",
                "category": "Indirect Tax",
                "frequency": ComplianceFrequency.MONTHLY,
                "applicability_rules": {"gst_registration": True},
                "due_date_rules": {"monthly": "20th of next month", "quarterly": "22nd/24th of month following quarter"},
                "period_rules": {"monthly": "calendar month", "quarterly": "calendar quarter"},
                "default_checklist": [
                    {"item": "Sales register", "mandatory": True},
                    {"item": "Purchase register", "mandatory": True},
                    {"item": "Input tax credit reconciliation", "mandatory": True},
                    {"item": "E-invoice data", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "GSTR-1", "mandatory": True},
                    {"document": "GSTR-3B", "mandatory": True},
                    {"document": "GSTR-9", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Compilation", "order": 1},
                    {"stage": "Reconciliation", "order": 2},
                    {"stage": "Review", "order": 3},
                    {"stage": "Filing", "order": 4},
                ],
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "TDS",
                "name": "TDS Return Filing",
                "description": "Quarterly TDS return filing (24Q, 26Q, 27Q, 27EQ)",
                "category": "Direct Tax",
                "frequency": ComplianceFrequency.QUARTERLY,
                "applicability_rules": {"tan_registration": True},
                "due_date_rules": {"quarterly": "31st of month following quarter"},
                "period_rules": {"quarterly": "calendar quarter"},
                "default_checklist": [
                    {"item": "Challan details", "mandatory": True},
                    {"item": "Deductee details", "mandatory": True},
                    {"item": "Salary details (24Q)", "mandatory": False},
                ],
                "default_document_requirements": [
                    {"document": "Form 24Q", "mandatory": True},
                    {"document": "Form 26Q", "mandatory": True},
                    {"document": "Form 27Q", "mandatory": False},
                    {"document": "Form 27EQ", "mandatory": False},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Validation", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "is_system": True,
                "is_active": True,
            },
            {
                "code": "MCA_ROC",
                "name": "MCA/ROC Filing",
                "description": "Annual MCA/ROC filing (AOC-4, MGT-7, ADT-1, DPT-3)",
                "category": "Corporate Law",
                "frequency": ComplianceFrequency.ANNUAL,
                "applicability_rules": {"entity_types": ["company", "llp"]},
                "due_date_rules": {"aoc4": "30 days from AGM", "mgt7": "60 days from AGM"},
                "period_rules": {"financial_year": "April to March"},
                "default_checklist": [
                    {"item": "Financial statements", "mandatory": True},
                    {"item": "Board report", "mandatory": True},
                    {"item": "AGM minutes", "mandatory": True},
                    {"item": "Auditor appointment", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "AOC-4", "mandatory": True},
                    {"document": "MGT-7", "mandatory": True},
                    {"document": "ADT-1", "mandatory": True},
                    {"document": "DPT-3", "mandatory": False},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Board Approval", "order": 2},
                    {"stage": "AGM", "order": 3},
                    {"stage": "Filing", "order": 4},
                ],
                "is_system": True,
                "is_active": True,
            },
        ]

        created = []
        for type_data in system_types:
            existing = await self.repository.get_type_by_code(type_data["code"], tenant_id)
            if not existing:
                compliance_type = ComplianceType(
                    **type_data,
                    tenant_id=tenant_id,
                )
                created.append(await self.repository.create_type(compliance_type))
        return created