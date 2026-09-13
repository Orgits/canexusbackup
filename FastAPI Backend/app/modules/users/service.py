from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ConflictException
from app.core.security import hash_password
from app.modules.users.models import User, Team
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.repository import UserRepository, TeamRepository


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = UserRepository(db)
        self.team_repository = TeamRepository(db)

    async def create(self, data: UserCreate, tenant_id: UUID) -> User:
        existing = await self.repository.get_by_email_and_tenant(data.email, tenant_id)
        if existing:
            raise ConflictException(detail="User with this email already exists in this tenant")

        hashed_password = hash_password(data.password)
        user_data = data.model_dump(exclude={"password"})
        user = User(**user_data, hashed_password=hashed_password, tenant_id=tenant_id)
        return await self.repository.create(user)

    async def get_by_id(self, user_id: UUID, tenant_id: UUID) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user or user.tenant_id != tenant_id:
            raise NotFoundException(detail="User not found")
        return user

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        team_id: Optional[UUID] = None,
    ) -> Tuple[List[User], int]:
        return await self.repository.get_all(tenant_id, page, page_size, search, is_active, role, team_id)

    async def update(self, user_id: UUID, tenant_id: UUID, data: UserUpdate) -> User:
        user = await self.get_by_id(user_id, tenant_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        return await self.repository.update(user)

    async def delete(self, user_id: UUID, tenant_id: UUID) -> None:
        user = await self.get_by_id(user_id, tenant_id)
        await self.repository.delete(user)

    async def update_password(self, user_id: UUID, tenant_id: UUID, new_password: str) -> User:
        user = await self.get_by_id(user_id, tenant_id)
        user.hashed_password = hash_password(new_password)
        return await self.repository.update(user)


class TeamService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = TeamRepository(db)

    async def create(self, tenant_id: UUID, name: str, description: Optional[str] = None, **kwargs) -> Team:
        team = Team(
            name=name,
            description=description,
            tenant_id=tenant_id,
            **kwargs,
        )
        return await self.repository.create(team)

    async def get_by_id(self, team_id: UUID, tenant_id: UUID) -> Team:
        team = await self.repository.get_by_id(team_id)
        if not team or team.tenant_id != tenant_id:
            raise NotFoundException(detail="Team not found")
        return team

    async def get_all(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Team], int]:
        return await self.repository.get_all(tenant_id, page, page_size, search, is_active)

    async def update(self, team_id: UUID, tenant_id: UUID, **kwargs) -> Team:
        team = await self.get_by_id(team_id, tenant_id)
        for field, value in kwargs.items():
            if hasattr(team, field):
                setattr(team, field, value)
        return await self.repository.update(team)

    async def delete(self, team_id: UUID, tenant_id: UUID) -> None:
        team = await self.get_by_id(team_id, tenant_id)
        await self.repository.delete(team)