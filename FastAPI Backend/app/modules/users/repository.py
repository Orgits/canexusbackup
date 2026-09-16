from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.users.models import Team, User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.tenant), selectinload(User.team))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_email_and_tenant(self, email: str, tenant_id: UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email, User.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
        role: str | None = None,
        team_id: UUID | None = None,
    ) -> tuple[list[User], int]:
        query = (
            select(User)
            .options(selectinload(User.tenant), selectinload(User.team))
            .where(User.tenant_id == tenant_id)
        )
        count_query = select(func.count(User.id)).where(User.tenant_id == tenant_id)

        if search:
            search_filter = or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.employee_id.ilike(f"%{search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        if role:
            query = query.where(User.roles.contains([role]))
            count_query = count_query.where(User.roles.contains([role]))

        if team_id:
            query = query.where(User.team_id == team_id)
            count_query = count_query.where(User.team_id == team_id)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, user: User) -> User:
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.db.delete(user)
        await self.db.flush()


class TeamRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, team: Team) -> Team:
        self.db.add(team)
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def get_by_id(self, team_id: UUID) -> Team | None:
        result = await self.db.execute(
            select(Team).options(selectinload(Team.lead)).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list[Team], int]:
        query = (
            select(Team)
            .options(selectinload(Team.lead))
            .where(Team.tenant_id == tenant_id)
        )
        count_query = select(func.count(Team.id)).where(Team.tenant_id == tenant_id)

        if search:
            query = query.where(Team.name.ilike(f"%{search}%"))
            count_query = count_query.where(Team.name.ilike(f"%{search}%"))

        if is_active is not None:
            query = query.where(Team.is_active == is_active)
            count_query = count_query.where(Team.is_active == is_active)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Team.created_at.desc())
        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def update(self, team: Team) -> Team:
        await self.db.flush()
        await self.db.refresh(team)
        return team

    async def delete(self, team: Team) -> None:
        await self.db.delete(team)
        await self.db.flush()
