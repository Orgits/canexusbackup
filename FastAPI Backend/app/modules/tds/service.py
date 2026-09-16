from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.modules.clients.models import Client
from app.modules.tds.models import (
    TDSChallan,
    TDSChallanStatus,
    TDSComplianceCycle,
    TDSDeductee,
    TDSDeducteeType,
    TDSFormType,
    TDSQuarter,
    TDSStatus,
)
from app.modules.tds.repository import TDSRepository
from app.modules.tds.schemas import (
    TDSChallanCreate,
    TDSChallanUpdate,
    TDSComplianceCycleCreate,
    TDSComplianceCycleUpdate,
    TDSDeducteeCreate,
    TDSDeducteeUpdate,
)


class TDSService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TDSRepository(db)

    # TDS Compliance Cycle methods
    async def create_cycle(
        self, data: TDSComplianceCycleCreate, tenant_id: UUID, created_by: UUID
    ) -> TDSComplianceCycle:
        # Verify client exists
        client_result = await self.db.execute(
            select(Client).where(Client.id == data.client_id, Client.tenant_id == tenant_id)
        )
        if not client_result.scalar_one_or_none():
            raise NotFoundException(detail="Client not found")

        # Check for duplicate
        existing_result = await self.db.execute(
            select(TDSComplianceCycle).where(
                TDSComplianceCycle.client_id == data.client_id,
                TDSComplianceCycle.form_type == TDSFormType(data.form_type),
                TDSComplianceCycle.financial_year == data.financial_year,
                TDSComplianceCycle.quarter == TDSQuarter(data.quarter),
                TDSComplianceCycle.tenant_id == tenant_id,
            )
        )
        if existing_result.scalar_one_or_none():
            raise ConflictException(detail="TDS cycle already exists for this client, form, FY, and quarter")

        cycle = TDSComplianceCycle(
            **data.model_dump(
                exclude={"form_type", "quarter", "status"}
            ),
            form_type=TDSFormType(data.form_type),
            quarter=TDSQuarter(data.quarter),
            status=TDSStatus.PENDING,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        return await self.repository.create_cycle(cycle)

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> TDSComplianceCycle:
        cycle = await self.repository.get_cycle_by_id(cycle_id, tenant_id)
        if not cycle:
            raise NotFoundException(detail="TDS compliance cycle not found")
        return cycle

    async def get_cycle_with_details(self, cycle_id: UUID, tenant_id: UUID) -> TDSComplianceCycle:
        cycle = await self.repository.get_cycle_with_details(cycle_id, tenant_id)
        if not cycle:
            raise NotFoundException(detail="TDS compliance cycle not found")
        return cycle

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        client_id: UUID | None = None,
        form_type: str | None = None,
        financial_year: str | None = None,
        quarter: str | None = None,
        status: str | None = None,
        matter_id: UUID | None = None,
        due_date_from: datetime | None = None,
        due_date_to: datetime | None = None,
        assigned_user_id: UUID | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> tuple[list[TDSComplianceCycle], int]:
        form_type_enum = None
        if form_type:
            try:
                form_type_enum = TDSFormType(form_type)
            except ValueError:
                raise ValidationException(detail=f"Invalid form_type: {form_type}")

        quarter_enum = None
        if quarter:
            try:
                quarter_enum = TDSQuarter(quarter)
            except ValueError:
                raise ValidationException(detail=f"Invalid quarter: {quarter}")

        status_enum = None
        if status:
            try:
                status_enum = TDSStatus(status)
            except ValueError:
                raise ValidationException(detail=f"Invalid status: {status}")

        return await self.repository.get_all_cycles(
            tenant_id,
            page,
            page_size,
            search,
            client_id,
            form_type_enum,
            financial_year,
            quarter_enum,
            status_enum,
            matter_id,
            due_date_from,
            due_date_to,
            assigned_user_id,
            sort_by,
            sort_order,
        )

    async def update_cycle(
        self, cycle_id: UUID, tenant_id: UUID, data: TDSComplianceCycleUpdate, updated_by: UUID
    ) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        # Handle enum fields
        if "form_type" in update_data:
            try:
                cycle.form_type = TDSFormType(update_data.pop("form_type"))
            except ValueError:
                raise ValidationException(detail="Invalid form_type")

        if "quarter" in update_data:
            try:
                cycle.quarter = TDSQuarter(update_data.pop("quarter"))
            except ValueError:
                raise ValidationException(detail="Invalid quarter")

        if "status" in update_data:
            try:
                cycle.status = TDSStatus(update_data.pop("status"))
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
    async def start_data_collection(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != TDSStatus.PENDING:
            raise ValidationException(detail="Can only start data collection from PENDING status")
        cycle.status = TDSStatus.DATA_COLLECTION
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def start_validation(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != TDSStatus.DATA_COLLECTION:
            raise ValidationException(detail="Can only start validation from DATA_COLLECTION status")
        cycle.status = TDSStatus.VALIDATION
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_ready_for_filing(self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != TDSStatus.VALIDATION:
            raise ValidationException(detail="Can only mark ready for filing from VALIDATION status")
        cycle.status = TDSStatus.READY_FOR_FILING
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_filed(
        self,
        cycle_id: UUID,
        tenant_id: UUID,
        actor_id: UUID,
        token_number: str,
        acknowledgment_number: str | None = None,
        filing_date: datetime | None = None,
    ) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status not in [TDSStatus.READY_FOR_FILING, TDSStatus.VALIDATION]:
            raise ValidationException(detail="Can only mark as filed from READY_FOR_FILING or VALIDATION status")

        cycle.status = TDSStatus.FILED
        cycle.filing_date = filing_date or datetime.now(UTC)
        cycle.token_number = token_number
        if acknowledgment_number:
            cycle.acknowledgment_number = acknowledgment_number
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    async def mark_processed(
        self, cycle_id: UUID, tenant_id: UUID, actor_id: UUID, processed_date: datetime | None = None
    ) -> TDSComplianceCycle:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)
        if cycle.status != TDSStatus.FILED:
            raise ValidationException(detail="Can only mark as processed from FILED status")

        cycle.status = TDSStatus.PROCESSED
        cycle.processed_date = processed_date or datetime.now(UTC)
        cycle.updated_by = actor_id
        return await self.repository.update_cycle(cycle)

    # Challan methods
    async def add_challan(
        self, cycle_id: UUID, data: TDSChallanCreate, tenant_id: UUID, created_by: UUID
    ) -> TDSChallan:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)

        total = (
            data.tax_amount
            + data.surcharge
            + data.education_cess
            + data.interest
            + data.penalty
            + data.fee
        )

        challan = TDSChallan(
            tds_cycle_id=cycle.id,
            **data.model_dump(),
            total_amount=total,
            tenant_id=tenant_id,
            created_by=created_by,
        )
        created = await self.repository.create_challan(challan)

        # Update cycle totals
        cycle.total_tax_deposited += total
        await self.repository.update_cycle(cycle)

        return created

    async def get_challan(self, challan_id: UUID, tenant_id: UUID) -> TDSChallan:
        challan = await self.repository.get_challan_by_id(challan_id, tenant_id)
        if not challan:
            raise NotFoundException(detail="Challan not found")
        return challan

    async def update_challan(
        self, challan_id: UUID, tenant_id: UUID, data: TDSChallanUpdate, updated_by: UUID
    ) -> TDSChallan:
        challan = await self.get_challan(challan_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        old_total = challan.total_amount

        if "status" in update_data:
            try:
                challan.status = TDSChallanStatus(update_data.pop("status"))
            except ValueError:
                raise ValidationException(detail="Invalid challan status")

        for field, value in update_data.items():
            setattr(challan, field, value)

        # Recalculate total if amounts changed
        if any(f in update_data for f in ["tax_amount", "surcharge", "education_cess", "interest", "penalty", "fee"]):
            challan.total_amount = (
                challan.tax_amount
                + challan.surcharge
                + challan.education_cess
                + challan.interest
                + challan.penalty
                + challan.fee
            )

        challan.updated_by = updated_by
        updated = await self.repository.update_challan(challan)

        # Update cycle totals
        cycle = await self.get_cycle_by_id(challan.tds_cycle_id, tenant_id)
        cycle.total_tax_deposited += (challan.total_amount - old_total)
        await self.repository.update_cycle(cycle)

        return updated

    async def verify_challan(self, challan_id: UUID, tenant_id: UUID, actor_id: UUID) -> TDSChallan:
        challan = await self.get_challan(challan_id, tenant_id)
        challan.status = TDSChallanStatus.VERIFIED
        challan.verified_at = datetime.now(UTC)
        challan.verified_by = actor_id
        challan.updated_by = actor_id
        return await self.repository.update_challan(challan)

    async def delete_challan(self, challan_id: UUID, tenant_id: UUID) -> None:
        challan = await self.get_challan(challan_id, tenant_id)

        # Update cycle totals
        cycle = await self.get_cycle_by_id(challan.tds_cycle_id, tenant_id)
        cycle.total_tax_deposited -= challan.total_amount
        await self.repository.update_cycle(cycle)

        await self.repository.delete_challan(challan)

    # Deductee methods
    async def add_deductee(
        self, cycle_id: UUID, data: TDSDeducteeCreate, tenant_id: UUID, created_by: UUID
    ) -> TDSDeductee:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)

        deductee = TDSDeductee(
            tds_cycle_id=cycle.id,
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by=created_by,
        )
        created = await self.repository.create_deductee(deductee)

        # Update cycle totals
        cycle.total_deductees += 1
        cycle.total_tax_deducted += data.tax_deducted
        cycle.total_tax_deposited += data.tax_deposited
        await self.repository.update_cycle(cycle)

        return created

    async def bulk_add_deductees(
        self, cycle_id: UUID, data_list: list[TDSDeducteeCreate], tenant_id: UUID, created_by: UUID
    ) -> list[TDSDeductee]:
        cycle = await self.get_cycle_by_id(cycle_id, tenant_id)

        deductees = [
            TDSDeductee(
                tds_cycle_id=cycle.id,
                **data.model_dump(),
                tenant_id=tenant_id,
                created_by=created_by,
            )
            for data in data_list
        ]

        created = await self.repository.bulk_create_deductees(deductees)

        # Update cycle totals
        cycle.total_deductees += len(created)
        cycle.total_tax_deducted += sum(d.tax_deducted for d in created)
        cycle.total_tax_deposited += sum(d.tax_deposited for d in created)
        await self.repository.update_cycle(cycle)

        return created

    async def get_deductee(self, deductee_id: UUID, tenant_id: UUID) -> TDSDeductee:
        deductee = await self.repository.get_deductee_by_id(deductee_id, tenant_id)
        if not deductee:
            raise NotFoundException(detail="Deductee not found")
        return deductee

    async def get_deductees_for_cycle(
        self, cycle_id: UUID, tenant_id: UUID, page: int = 1, page_size: int = 100
    ) -> tuple[list[TDSDeductee], int]:
        return await self.repository.get_deductees_for_cycle(cycle_id, tenant_id, page, page_size)

    async def update_deductee(
        self, deductee_id: UUID, tenant_id: UUID, data: TDSDeducteeUpdate, updated_by: UUID
    ) -> TDSDeductee:
        deductee = await self.get_deductee(deductee_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)

        old_tax_deducted = deductee.tax_deducted
        old_tax_deposited = deductee.tax_deposited

        if "deductee_type" in update_data:
            try:
                deductee.deductee_type = TDSDeducteeType(update_data.pop("deductee_type"))
            except ValueError:
                raise ValidationException(detail="Invalid deductee type")

        for field, value in update_data.items():
            setattr(deductee, field, value)

        deductee.updated_by = updated_by
        updated = await self.repository.update_deductee(deductee)

        # Update cycle totals
        cycle = await self.get_cycle_by_id(deductee.tds_cycle_id, tenant_id)
        cycle.total_tax_deducted += (deductee.tax_deducted - old_tax_deducted)
        cycle.total_tax_deposited += (deductee.tax_deposited - old_tax_deposited)
        await self.repository.update_cycle(cycle)

        return updated

    async def delete_deductee(self, deductee_id: UUID, tenant_id: UUID) -> None:
        deductee = await self.get_deductee(deductee_id, tenant_id)

        cycle = await self.get_cycle_by_id(deductee.tds_cycle_id, tenant_id)
        cycle.total_deductees -= 1
        cycle.total_tax_deducted -= deductee.tax_deducted
        cycle.total_tax_deposited -= deductee.tax_deposited
        await self.repository.update_cycle(cycle)

        await self.repository.delete_deductee(deductee)

    async def get_summary(self, tenant_id: UUID, financial_year: str | None = None) -> dict:
        return await self.repository.get_summary(tenant_id, financial_year)
