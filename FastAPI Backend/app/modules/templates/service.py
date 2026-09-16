from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.modules.templates.models import Template, TemplateStatus
from app.modules.templates.repository import TemplateRepository
from app.modules.templates.schemas import TemplateCreate, TemplateUpdate, TemplateVersionCreate
from app.modules.users.models import User


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TemplateRepository(db)

    async def create(self, data: TemplateCreate, tenant_id: UUID, created_by: UUID) -> Template:
        # Check for duplicate name
        existing = await self.repository.get_by_name(data.name, tenant_id)
        if existing:
            raise ValueError("Template with this name already exists")

        template = Template(
            **data.model_dump(),
            tenant_id=tenant_id,
            created_by_id=created_by,
            status=TemplateStatus.DRAFT,
        )
        return await self.repository.create(template)

    async def get_by_id(self, template_id: UUID, tenant_id: UUID) -> Template:
        template = await self.repository.get_by_id(template_id, tenant_id)
        if not template:
            raise NotFoundException(detail="Template not found")
        return template

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        status: str | None = None,
        category: str | None = None,
        channel: str | None = None,
        is_default: bool | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
    ) -> tuple[list[Template], int]:
        return await self.repository.get_all(
            tenant_id, page, page_size, search, status, category, channel, is_default, sort_by, sort_order
        )

    async def update(
        self, template_id: UUID, tenant_id: UUID, data: TemplateUpdate, updated_by: UUID
    ) -> Template:
        template = await self.get_by_id(template_id, tenant_id)

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(template, field, value)

        template.updated_at = datetime.now()
        return await self.repository.update(template)

    async def delete(self, template_id: UUID, tenant_id: UUID) -> None:
        template = await self.get_by_id(template_id, tenant_id)
        await self.repository.delete(template)

    async def create_version(
        self, template_id: UUID, tenant_id: UUID, data: TemplateVersionCreate, created_by: UUID
    ) -> Template:
        template = await self.get_by_id(template_id, tenant_id)

        # Create new version
        new_version = template.version + 1

        new_template = Template(
            name=template.name,
            description=template.description,
            category=template.category,
            subject=data.subject or template.subject,
            content=data.content,
            content_html=data.content_html or template.content_html,
            variables=data.variables or template.variables,
            channel=template.channel,
            language=template.language,
            version=new_version,
            is_default=False,
            metadata=template.metadata.copy(),
            tenant_id=tenant_id,
            created_by_id=created_by,
            status=TemplateStatus.DRAFT,
        )

        self.db.add(new_template)
        await self.db.flush()
        await self.db.refresh(new_template)

        return new_template

    async def set_default(self, template_id: UUID, tenant_id: UUID) -> Template:
        template = await self.get_by_id(template_id, tenant_id)

        # Unset current default
        await self.db.execute(
            select(Template).where(
                Template.tenant_id == tenant_id,
                Template.channel == template.channel,
                Template.is_default == True,
            )
        )
        result = await self.db.execute(
            select(Template).where(
                Template.tenant_id == tenant_id,
                Template.channel == template.channel,
                Template.is_default == True,
            )
        )
        current_default = result.scalars().first()
        if current_default:
            current_default.is_default = False

        template.is_default = True
        template.status = TemplateStatus.ACTIVE
        await self.db.flush()
        await self.db.refresh(template)

        return template

    async def activate(self, template_id: UUID, tenant_id: UUID) -> Template:
        template = await self.get_by_id(template_id, tenant_id)
        template.status = TemplateStatus.ACTIVE
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def archive(self, template_id: UUID, tenant_id: UUID) -> Template:
        template = await self.get_by_id(template_id, tenant_id)
        template.status = TemplateStatus.ARCHIVED
        await self.db.flush()
        await self.db.refresh(template)
        return template