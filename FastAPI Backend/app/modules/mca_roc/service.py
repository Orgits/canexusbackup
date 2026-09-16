from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.modules.clients.models import Client
from app.modules.mca_roc.models import (
    MCAEntityType,
    MCAFilingCategory,
    MCAFilingConfig,
    MCAFilingCycle,
    MCAFilingType,
    MCAStatus,
)
from app.modules.mca_roc.repository import MCARepository
from app.modules.mca_roc.schemas import (
    MCAFilingConfigCreate,
    MCAFilingConfigUpdate,
    MCAFilingCycleCreate,
    MCAFilingCycleUpdate,
)


class MCAService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = MCARepository(db)

    # MCA Filing Config methods
    async def create_config(
        self, data: MCAFilingConfigCreate, tenant_id: UUID, created_by: UUID
    ) -> MCAFilingConfig:
        filing_type = MCAFilingType(data.filing_type)
        existing = await self.repository.get_config_by_filing_type(filing_type, tenant_id)
        if existing:
            raise ConflictException(detail="MCA filing config for this type already exists")

        config = MCAFilingConfig(
            **data.model_dump(
                exclude={"filing_type", "entity_type", "filing_category"}
            ),
            filing_type=filing_type,
            entity_type=MCAEntityType(data.entity_type),
            filing_category=MCAFilingCategory(data.filing_category),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_config(config)

    async def get_config_by_id(self, config_id: UUID, tenant_id: UUID) -> MCAFilingConfig:
        config = await self.repository.get_config_by_id(config_id, tenant_id)
        if not config:
            raise NotFoundException(detail="MCA filing config not found")
        return config

    async def get_all_configs(
        self,
        tenant_id: UUID,
        entity_type: str | None = None,
        filing_category: str | None = None,
        is_active: bool | None = None,
    ) -> list[MCAFilingConfig]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = MCAEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        filing_category_enum = None
        if filing_category:
            try:
                filing_category_enum = MCAFilingCategory(filing_category)
            except ValueError:
                raise ValidationException(detail=f"Invalid filing_category: {filing_category}")

        return await self.repository.get_all_configs(tenant_id, entity_type_enum, filing_category_enum, is_active)

    async def update_config(
        self, config_id: UUID, tenant_id: UUID, data: MCAFilingConfigUpdate, updated_by: UUID
    ) -> MCAFilingConfig:
        config = await self.get_config_by_id(config_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(config, field, value)
        config.updated_by = updated_by
        return await self.repository.update_config(config)

    async def delete_config(self, config_id: UUID, tenant_id: UUID) -> None:
        config = await self.get_config_by_id(config_id, tenant_id)
        if config.is_system:
            raise ConflictException(detail="Cannot delete system config")
        await self.repository.delete_config(config)

    async def initialize_system_configs(self, tenant_id: UUID) -> list[MCAFilingConfig]:
        return await self.repository.initialize_system_configs(tenant_id)

    # MCA Filing Cycle methods
    async def create_cycle(
        self, data: MCAFilingCycleCreate, tenant_id: UUID, created_by: UUID
    ) -> MCAFilingCycle:
        # Verify client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Get config for defaults
        filing_type = MCAFilingType(data.filing_type)
        config = await self.repository.get_config_by_filing_type(filing_type, tenant_id)

        cycle = MCAFilingCycle(
            **data.model_dump(
                exclude={"filing_type", "entity_type", "filing_category", "status"}
            ),
            entity_type=MCAEntityType(data.entity_type),
            filing_type=filing_type,
            filing_category=MCAFilingCategory(data.filing_category),
            status=MCAStatus.PENDING,
            tenant_id=tenant_id,
            created_by=created_by,
        )

        # Apply defaults from config if available
        if config:
            if not cycle.checklist:
                cycle.checklist = config.default_checklist
            if not cycle.document_requirements:
                cycle.document_requirements = config.default_document_requirements
            if not cycle.workflow_stages:
                cycle.workflow_stages = config.default_workflow_stages

        return await self.repository.create_cycle(cycle)

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> MCAFilingCycle:
        cycle = await self.repository.get_cycle_by_id(cycle_id, tenant_id)
        if not cycle:
            raise NotFoundException(detail="MCA filing cycle not found")
        return cycle

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        entity_type: str | None = None,
        filing_type: str | None = None,
        filing_category: str | None = None,
        financial_year: str | None = None,
        status: str | None = None,
        matter_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        assigned_user_id: UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[MCAFilingCycle], int]:
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = MCAEntityType(entity_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid entity_type: {entity_type}")

        filing_type_enum = None
        if filing_type:
            try:
                filing_type_enum = MCAFilingType(filing_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid filing_type: {filing_type}")

        filing_category_enum = None
        if filing_category:
            try:
                filing_category_enum = MCAFilingCategory(filing_category)
            except ValueError:
                raise ValidationException(detail=f"Invalid filing_category: {filing_category}")

        status_enum = None
        if status:
            try:
                status_enum = MCAStatus(status)
            except ValueError:
                raise ValidationException(detail=f"Invalid status: {status}")

        return await self.repository.get_all_cycles(
            tenant_id,
            page,
            page_size,
            search,
            client_id,
            entity_type_enum,
            filing_type_enum,
            filing_category_enum,
            financial_year,
            status_enum,
            matter_id,
            due_date_from,
            due_date_to,
            assigned_user_id,
            sort_by,
            sort_order,
        )

    async def update_cycle(
        self, cycle_id: UUID, tenant_id: UUID, data: MCAFilingCycleUpdate, updated_by: UUID
    ) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        # Handle enum fields
        if "entity_type" in update_data:
            try:
                cycle.entity_type = MCAEntityType(update_data.pop("entity_type"))
            except ValueError:
                raise ValidationException(detail="Invalid entity_type")

        if "filing_type" in update_data:
            try:
                cycle.filing_type = MCAFilingType(update_data.pop("filing_type"))
            except ValueError:
                raise ValidationException(detail="Invalid filing_type")

        if "filing_category" in update_data:
            try:
                cycle.filing_category = MCAFilingCategory(update_data.pop("filing_category"))
            except ValueError:
                raise ValidationException(detail="Invalid filing_category")

        if "status" in update_data:
            try:
                cycle.status = MCAStatus(update_data.pop("status"))
            except ValueError:
                raise ValidationException(detail="Invalid status")

        for field, value in update_data.items():
            setattr(cycle, field, value)
        cycle.updated_by = updated_by
        return await self.repository.update_cycle(cycle)

    async def delete_cycle(self, cycle_id: UUID, tenant_id: UUID) -> None:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        await self.repository.delete_cycle(cycle)

    # Status transition methods
    async def start_document_collection(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.PENDING:
            raise ValidationException(detail="Can only start document collection from PENDING status")
        cycle.status = MCAStatus.DOCUMENT_COLLECTION
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def start_preparation(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.DOCUMENT_COLLECTION:
            raise ValidationException(detail="Can only start preparation from DOCUMENT_COLLECTION status")
        cycle.status = MCAStatus.PREPARATION
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def start_review(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.PREPARATION:
            raise ValidationException(detail="Can only start review from PREPARATION status")
        cycle.status = MCAStatus.REVIEW
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def complete_board_approval(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.REVIEW:
            raise ValidationException(detail="Can only complete board approval from REVIEW status")
        cycle.status = MCAStatus.BOARD_APPROVAL
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def complete_agm(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID, agm_date: datetime) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.BOARD_APPROVAL:
            raise ValidationException(detail="Can only complete AGM from BOARD_APPROVAL status")
        cycle.status = MCAStatus.AGM_COMPLETED
        cycle.agm_date = agm_date
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_ready_for_filing(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.AGM_COMPLETED:
            raise ValidationException(detail="Can only mark ready for filing from AGM_COMPLETED status")
        cycle.status = MCAStatus.READY_FOR_FILING
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_filed(
        self,
        cycle_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
        srn: str,
        acknowledgment_number: str | None = None,
        filing_date: datetime | None = None,
        challan_amount: float = 0,
        additional_fee: float = 0,
    ) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.READY_FOR_FILING:
            raise ValidationException(detail="Can only mark as filed from READY_FOR_FILING status")

        cycle.status = MCAStatus.FILED
        cycle.filing_date = filing_date or datetime.now(UTC)
        cycle.srn = srn
        if acknowledgment_number:
            cycle.acknowledgment_number = acknowledgment_number
        cycle.challan_amount = challan_amount
        cycle.additional_fee = additional_fee
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_approved(
        self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID, approval_date: datetime | None = None
    ) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.FILED:
            raise ValidationException(detail="Can only mark as approved from FILED status")

        cycle.status = MCAStatus.APPROVED
        cycle.approval_date = approval_date or datetime.now(UTC)
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_rejected(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.FILED:
            raise ValidationException(detail="Can only mark as rejected from FILED status")

        cycle.status = MCAStatus.REJECTED
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_defective(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != MCAStatus.FILED:
            raise ValidationException(detail="Can only mark as defective from FILED status")

        cycle.status = MCAStatus.DEFECTIVE
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_resubmitted(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status not in [MCAStatus.REJECTED, MCAStatus.DEFECTIVE]:
            raise ValidationException(detail="Can only resubmit from REJECTED or DEFECTIVE status")

        cycle.status = MCAStatus.RESUBMITTED
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_completed(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> MCAFilingCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status not in [MCAStatus.APPROVED, MCAStatus.RESUBMITTED]:
            raise ValidationException(detail="Can only mark as completed from APPROVED or RESUBMITTED status")

        cycle.status = MCAStatus.COMPLETED
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def get_summary(self, tenant_id: UUID, financial_year: str | None = None) -> dict:
        return await self.repository.get_summary(tenant_id, financial_year)
