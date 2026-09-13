from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.modules.mca_roc.models import (
    MCAFilingCycle,
    MCAFilingConfig,
    MCAEntityType,
    MCAFilingType,
    MCAFilingCategory,
    MCAStatus,
)
from app.modules.mca_roc.schemas import (
    MCAFilingCycleCreate,
    MCAFilingCycleUpdate,
    MCAFilingConfigCreate,
    MCAFilingConfigUpdate,
)


class MCARepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # MCA Filing Config methods
    async def create_config(self, config: MCAFilingConfig) -> MCAFilingConfig:
        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def get_config_by_id(self, config_id: UUID, tenant_id: UUID) -> Optional[MCAFilingConfig]:
        result = await self.db.execute(
            select(MCAFilingConfig).where(
                MCAFilingConfig.id == config_id,
                MCAFilingConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_config_by_filing_type(self, filing_type: MCAFilingType, tenant_id: UUID) -> Optional[MCAFilingConfig]:
        result = await self.db.execute(
            select(MCAFilingConfig).where(
                MCAFilingConfig.filing_type == filing_type,
                MCAFilingConfig.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_configs(
        self,
        tenant_id: UUID,
        entity_type: Optional[MCAEntityType] = None,
        filing_category: Optional[MCAFilingCategory] = None,
        is_active: Optional[bool] = None,
    ) -> List[MCAFilingConfig]:
        query = select(MCAFilingConfig).where(MCAFilingConfig.tenant_id == tenant_id)

        if entity_type:
            query = query.where(MCAFilingConfig.entity_type == entity_type)
        if filing_category:
            query = query.where(MCAFilingConfig.filing_category == filing_category)
        if is_active is not None:
            query = query.where(MCAFilingConfig.is_active == is_active)

        query = query.order_by(MCAFilingConfig.filing_type)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_config(self, config: MCAFilingConfig) -> MCAFilingConfig:
        await self.db.flush()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config: MCAFilingConfig) -> None:
        await self.db.delete(config)
        await self.db.flush()

    # MCA Filing Cycle methods
    async def create_cycle(self, cycle: MCAFilingCycle) -> MCAFilingCycle:
        self.db.add(cycle)
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def get_cycle_by_id(self, cycle_id: UUID, tenant_id: UUID) -> Optional[MCAFilingCycle]:
        result = await self.db.execute(
            select(MCAFilingCycle)
            .where(
                MCAFilingCycle.id == cycle_id,
                MCAFilingCycle.tenant_id == tenant_id,
            )
            .options(
                selectinload(MCAFilingCycle.client),
                selectinload(MCAFilingCycle.matter),
                selectinload(MCAFilingCycle.assigned_user),
                selectinload(MCAFilingCycle.assigned_team),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_cycles(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        client_id: Optional[UUID] = None,
        entity_type: Optional[MCAEntityType] = None,
        filing_type: Optional[MCAFilingType] = None,
        filing_category: Optional[MCAFilingCategory] = None,
        financial_year: Optional[str] = None,
        status: Optional[MCAStatus] = None,
        matter_id: Optional[UUID] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        assigned_user_id: Optional[UUID] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
    ) -> Tuple[List[MCAFilingCycle], int]:
        query = select(MCAFilingCycle).where(MCAFilingCycle.tenant_id == tenant_id)
        count_query = select(func.count(MCAFilingCycle.id)).where(MCAFilingCycle.tenant_id == tenant_id)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    MCAFilingCycle.filing_type.ilike(search_term),
                    MCAFilingCycle.financial_year.ilike(search_term),
                    MCAFilingCycle.company_name.ilike(search_term),
                    MCAFilingCycle.cin_llpin.ilike(search_term),
                )
            )
            count_query = count_query.where(
                or_(
                    MCAFilingCycle.filing_type.ilike(search_term),
                    MCAFilingCycle.financial_year.ilike(search_term),
                    MCAFilingCycle.company_name.ilike(search_term),
                    MCAFilingCycle.cin_llpin.ilike(search_term),
                )
            )

        if client_id:
            query = query.where(MCAFilingCycle.client_id == client_id)
            count_query = count_query.where(MCAFilingCycle.client_id == client_id)

        if entity_type:
            query = query.where(MCAFilingCycle.entity_type == entity_type)
            count_query = count_query.where(MCAFilingCycle.entity_type == entity_type)

        if filing_type:
            query = query.where(MCAFilingCycle.filing_type == filing_type)
            count_query = count_query.where(MCAFilingCycle.filing_type == filing_type)

        if filing_category:
            query = query.where(MCAFilingCycle.filing_category == filing_category)
            count_query = count_query.where(MCAFilingCycle.filing_category == filing_category)

        if financial_year:
            query = query.where(MCAFilingCycle.financial_year == financial_year)
            count_query = count_query.where(MCAFilingCycle.financial_year == financial_year)

        if status:
            query = query.where(MCAFilingCycle.status == status)
            count_query = count_query.where(MCAFilingCycle.status == status)

        if matter_id:
            query = query.where(MCAFilingCycle.matter_id == matter_id)
            count_query = count_query.where(MCAFilingCycle.matter_id == matter_id)

        if due_date_from:
            query = query.where(MCAFilingCycle.due_date >= due_date_from)
            count_query = count_query.where(MCAFilingCycle.due_date >= due_date_from)

        if due_date_to:
            query = query.where(MCAFilingCycle.due_date <= due_date_to)
            count_query = count_query.where(MCAFilingCycle.due_date <= due_date_to)

        if assigned_user_id:
            query = query.where(MCAFilingCycle.assigned_user_id == assigned_user_id)
            count_query = count_query.where(MCAFilingCycle.assigned_user_id == assigned_user_id)

        if sort_by and hasattr(MCAFilingCycle, sort_by):
            column = getattr(MCAFilingCycle, sort_by)
            if sort_order == "desc":
                query = query.order_by(column.desc())
            else:
                query = query.order_by(column.asc())
        else:
            query = query.order_by(MCAFilingCycle.due_date.asc())

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.db.execute(
            query.options(
                selectinload(MCAFilingCycle.client),
                selectinload(MCAFilingCycle.matter),
                selectinload(MCAFilingCycle.assigned_user),
                selectinload(MCAFilingCycle.assigned_team),
            )
        )
        cycles = result.scalars().all()

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return list(cycles), total

    async def update_cycle(self, cycle: MCAFilingCycle) -> MCAFilingCycle:
        await self.db.flush()
        await self.db.refresh(cycle)
        return cycle

    async def delete_cycle(self, cycle: MCAFilingCycle) -> None:
        await self.db.delete(cycle)
        await self.db.flush()

    async def get_summary(self, tenant_id: UUID, financial_year: Optional[str] = None) -> dict:
        query = select(MCAFilingCycle).where(MCAFilingCycle.tenant_id == tenant_id)
        if financial_year:
            query = query.where(MCAFilingCycle.financial_year == financial_year)

        result = await self.db.execute(query)
        cycles = result.scalars().all()

        total = len(cycles)
        pending = sum(1 for c in cycles if c.status == MCAStatus.PENDING)
        in_progress = sum(1 for c in cycles if c.status in [
            MCAStatus.DOCUMENT_COLLECTION, MCAStatus.PREPARATION, MCAStatus.REVIEW,
            MCAStatus.BOARD_APPROVAL, MCAStatus.AGM_COMPLETED, MCAStatus.READY_FOR_FILING
        ])
        ready_for_filing = sum(1 for c in cycles if c.status == MCAStatus.READY_FOR_FILING)
        filed = sum(1 for c in cycles if c.status == MCAStatus.FILED)
        approved = sum(1 for c in cycles if c.status == MCAStatus.APPROVED)
        rejected = sum(1 for c in cycles if c.status == MCAStatus.REJECTED)
        overdue = sum(1 for c in cycles if c.status == MCAStatus.OVERDUE)

        # Upcoming deadlines (next 30 days)
        upcoming_date = datetime.now(timezone.utc) + timedelta(days=30)
        upcoming = [
            c for c in cycles
            if c.status not in [MCAStatus.FILED, MCAStatus.APPROVED, MCAStatus.COMPLETED, MCAStatus.CANCELLED]
            and c.due_date <= upcoming_date
        ]
        upcoming.sort(key=lambda x: x.due_date)

        return {
            "total_filings": total,
            "pending": pending,
            "in_progress": in_progress,
            "ready_for_filing": ready_for_filing,
            "filed": filed,
            "approved": approved,
            "rejected": rejected,
            "overdue": overdue,
            "upcoming_deadlines": upcoming[:10],
        }

    async def initialize_system_configs(self, tenant_id: UUID) -> List[MCAFilingConfig]:
        system_configs = [
            # Company Annual Filings
            {
                "filing_type": MCAFilingType.AOC_4,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Financial Statements (AOC-4)",
                "description": "Filing of financial statements with ROC",
                "form_name": "AOC-4",
                "due_date_rule": {"rule": "30 days from AGM"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Audited financial statements", "mandatory": True},
                    {"item": "Board report", "mandatory": True},
                    {"item": "Auditor's report", "mandatory": True},
                    {"item": "AGM minutes", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "Balance Sheet", "mandatory": True},
                    {"document": "Profit & Loss", "mandatory": True},
                    {"document": "Cash Flow Statement", "mandatory": True},
                    {"document": "Notes to Accounts", "mandatory": True},
                    {"document": "Auditor's Report", "mandatory": True},
                    {"document": "Board Report", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Collection", "order": 1},
                    {"stage": "Preparation", "order": 2},
                    {"stage": "Review", "order": 3},
                    {"stage": "Board Approval", "order": 4},
                    {"stage": "AGM", "order": 5},
                    {"stage": "Filing", "order": 6},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.AOC_4_XBRL,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Financial Statements XBRL (AOC-4 XBRL)",
                "description": "XBRL filing of financial statements",
                "form_name": "AOC-4 XBRL",
                "due_date_rule": {"rule": "30 days from AGM"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "XBRL instance document", "mandatory": True},
                    {"item": "Financial statements in XBRL", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "XBRL Instance Document", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "XBRL Preparation", "order": 1},
                    {"stage": "Validation", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.MGT_7,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Annual Return (MGT-7)",
                "description": "Annual return filing for companies",
                "form_name": "MGT-7",
                "due_date_rule": {"rule": "60 days from AGM"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Shareholding pattern", "mandatory": True},
                    {"item": "Directors details", "mandatory": True},
                    {"item": "Meeting details", "mandatory": True},
                    {"item": "Remuneration details", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "MGT-7 Form", "mandatory": True},
                    {"document": "Shareholding pattern", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Preparation", "order": 2},
                    {"stage": "Review", "order": 3},
                    {"stage": "Board Approval", "order": 4},
                    {"stage": "Filing", "order": 5},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.MGT_7A,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Annual Return - Small Companies/OPC (MGT-7A)",
                "description": "Abridged annual return for small companies and OPCs",
                "form_name": "MGT-7A",
                "due_date_rule": {"rule": "60 days from AGM"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Basic company details", "mandatory": True},
                    {"item": "Shareholding", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "MGT-7A Form", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.ADT_1,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Auditor Appointment (ADT-1)",
                "description": "Appointment of auditor",
                "form_name": "ADT-1",
                "due_date_rule": {"rule": "15 days from appointment"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Board resolution", "mandatory": True},
                    {"item": "Auditor consent", "mandatory": True},
                    {"item": "Auditor eligibility certificate", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "ADT-1 Form", "mandatory": True},
                    {"document": "Board Resolution", "mandatory": True},
                    {"document": "Auditor Consent", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.DPT_3,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Return of Deposits (DPT-3)",
                "description": "Return of deposits or particulars of transactions not considered as deposits",
                "form_name": "DPT-3",
                "due_date_rule": {"rule": "30 June"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Deposit details", "mandatory": True},
                    {"item": "Particulars of transactions", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "DPT-3 Form", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Preparation", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.MSME_1,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "MSME Return (MSME-1)",
                "description": "Half-yearly return for outstanding payments to MSMEs",
                "form_name": "MSME-1",
                "due_date_rule": {"rule": "Half-yearly (31 Oct / 30 Apr)"},
                "period_rule": {"half_yearly": "Apr-Sep / Oct-Mar"},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Outstanding MSME payments", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "MSME-1 Form", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.DIR_3_KYC,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Director KYC (DIR-3 KYC)",
                "description": "Annual KYC of directors",
                "form_name": "DIR-3 KYC",
                "due_date_rule": {"rule": "30 September"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Director details", "mandatory": True},
                    {"item": "DIN verification", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "DIR-3 KYC Form", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            # LLP Annual Filings
            {
                "filing_type": MCAFilingType.FORM_8,
                "entity_type": MCAEntityType.LLP,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Statement of Account & Solvency (Form 8)",
                "description": "LLP statement of account and solvency",
                "form_name": "Form 8",
                "due_date_rule": {"rule": "30 October"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Statement of accounts", "mandatory": True},
                    {"item": "Solvency declaration", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "Form 8", "mandatory": True},
                    {"document": "Balance Sheet", "mandatory": True},
                    {"document": "Profit & Loss", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Preparation", "order": 1},
                    {"stage": "Review", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.FORM_11,
                "entity_type": MCAEntityType.LLP,
                "filing_category": MCAFilingCategory.ANNUAL,
                "name": "Annual Return of LLP (Form 11)",
                "description": "Annual return of LLP",
                "form_name": "Form 11",
                "due_date_rule": {"rule": "30 May"},
                "period_rule": {"financial_year": "April to March"},
                "is_annual": True,
                "default_checklist": [
                    {"item": "Partner details", "mandatory": True},
                    {"item": "Contribution details", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "Form 11", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Data Collection", "order": 1},
                    {"stage": "Preparation", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.FORM_3,
                "entity_type": MCAEntityType.LLP,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "LLP Agreement (Form 3)",
                "description": "Information about LLP agreement and changes",
                "form_name": "Form 3",
                "due_date_rule": {"rule": "30 days from execution"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "LLP Agreement", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "Form 3", "mandatory": True},
                    {"document": "LLP Agreement", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.FORM_4,
                "entity_type": MCAEntityType.LLP,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Change in Partners (Form 4)",
                "description": "Notice of appointment/cessation of partners",
                "form_name": "Form 4",
                "due_date_rule": {"rule": "30 days from change"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Consent of incoming partner", "mandatory": True},
                    {"item": "Resignation letter", "mandatory": False},
                ],
                "default_document_requirements": [
                    {"document": "Form 4", "mandatory": True},
                    {"document": "Consent Letter", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            # Event-based Company Filings
            {
                "filing_type": MCAFilingType.SH_7,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Increase in Authorized Capital (SH-7)",
                "description": "Notice of increase in authorized share capital",
                "form_name": "SH-7",
                "due_date_rule": {"rule": "30 days from resolution"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Board resolution", "mandatory": True},
                    {"item": "Shareholder resolution", "mandatory": True},
                    {"item": "Altered MOA", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "SH-7 Form", "mandatory": True},
                    {"document": "Board Resolution", "mandatory": True},
                    {"document": "Shareholder Resolution", "mandatory": True},
                    {"document": "Altered MOA", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Board Approval", "order": 2},
                    {"stage": "Shareholder Approval", "order": 3},
                    {"stage": "Filing", "order": 4},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.PAS_3,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Return of Allotment (PAS-3)",
                "description": "Return of allotment of shares",
                "form_name": "PAS-3",
                "due_date_rule": {"rule": "15 days from allotment"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Board resolution", "mandatory": True},
                    {"item": "Shareholder list", "mandatory": True},
                    {"item": "Valuation report", "mandatory": False},
                ],
                "default_document_requirements": [
                    {"document": "PAS-3 Form", "mandatory": True},
                    {"document": "Board Resolution", "mandatory": True},
                    {"document": "Shareholder List", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 10000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.DIR_12,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Change in Directors (DIR-12)",
                "description": "Appointment/cessation of directors",
                "form_name": "DIR-12",
                "due_date_rule": {"rule": "30 days from change"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Board resolution", "mandatory": True},
                    {"item": "DIR-2 consent", "mandatory": True},
                    {"item": "Resignation letter", "mandatory": False},
                ],
                "default_document_requirements": [
                    {"document": "DIR-12 Form", "mandatory": True},
                    {"document": "Board Resolution", "mandatory": True},
                    {"document": "DIR-2 Consent", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.INC_22,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Change of Registered Office (INC-22)",
                "description": "Notice of change of registered office",
                "form_name": "INC-22",
                "due_date_rule": {"rule": "30 days from change"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Board resolution", "mandatory": True},
                    {"item": "Proof of new address", "mandatory": True},
                    {"item": "NOC from owner", "mandatory": True},
                ],
                "default_document_requirements": [
                    {"document": "INC-22 Form", "mandatory": True},
                    {"document": "Board Resolution", "mandatory": True},
                    {"document": "Address Proof", "mandatory": True},
                    {"document": "NOC", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Board Approval", "order": 2},
                    {"stage": "Filing", "order": 3},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
            {
                "filing_type": MCAFilingType.MGT_14,
                "entity_type": MCAEntityType.COMPANY,
                "filing_category": MCAFilingCategory.EVENT_BASED,
                "name": "Board/Shareholder Resolutions (MGT-14)",
                "description": "Filing of resolutions with ROC",
                "form_name": "MGT-14",
                "due_date_rule": {"rule": "30 days from resolution"},
                "period_rule": {"event_based": True},
                "is_annual": False,
                "default_checklist": [
                    {"item": "Certified true copy of resolution", "mandatory": True},
                    {"item": "Explanatory statement", "mandatory": False},
                ],
                "default_document_requirements": [
                    {"document": "MGT-14 Form", "mandatory": True},
                    {"document": "Resolution", "mandatory": True},
                ],
                "default_workflow_stages": [
                    {"stage": "Document Preparation", "order": 1},
                    {"stage": "Filing", "order": 2},
                ],
                "base_fee": 0,
                "additional_fee_per_day": 100,
                "max_additional_fee": 5000,
                "is_system": True,
                "is_active": True,
            },
        ]

        created = []
        for config_data in system_configs:
            existing = await self.get_config_by_filing_type(config_data["filing_type"], tenant_id)
            if not existing:
                config = MCAFilingConfig(
                    **config_data,
                    tenant_id=tenant_id,
                )
                created.append(await self.create_config(config))
        return created