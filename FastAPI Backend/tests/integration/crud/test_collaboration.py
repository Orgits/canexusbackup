# Collaboration CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.collaboration.models import Comment, CommentAttachment, CommentReaction, CommentType
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter, MatterType, MatterStatus, MatterPriority
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestCollaborationCRUD:
    """Tests for Collaboration CRUD operations."""

    @pytest_asyncio.fixture
    async def test_firm(self, db_session: AsyncSession) -> Firm:
        firm = Firm(name="Test Firm", is_active=True, settings={}, country="India")
        db_session.add(firm)
        await db_session.flush()
        await db_session.refresh(firm)
        return firm

    @pytest_asyncio.fixture
    async def test_user(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="user@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Test User",
            tenant_id=test_firm.id,
            roles=["associate"],
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def test_client(self, db_session: AsyncSession, test_firm: Firm, test_user: User) -> Client:
        client = Client(name="Test Client", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=test_user.id)
        db_session.add(client)
        await db_session.flush()
        await db_session.refresh(client)
        return client

    @pytest_asyncio.fixture
    async def test_matter(self, db_session: AsyncSession, test_firm: Firm, test_client: Client, test_user: User) -> Matter:
        matter = Matter(
            name="Test Matter",
            matter_type=MatterType.TAX,
            status=MatterStatus.IN_PROGRESS,
            priority=MatterPriority.HIGH,
            client_id=test_client.id,
            responsible_user_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(matter)
        await db_session.flush()
        await db_session.refresh(matter)
        return matter

    @pytest.mark.integration
    async def test_create_comment(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        comment = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="This is a test comment",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(comment)
        await db_session.flush()
        await db_session.refresh(comment)

        assert comment.id is not None
        assert comment.entity_type == "matter"
        assert comment.content == "This is a test comment"
        assert comment.author_id == test_user.id

    @pytest.mark.integration
    async def test_create_comment_reply(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        parent_comment = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="Parent comment",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(parent_comment)
        await db_session.flush()

        reply = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="Reply to parent",
            author_id=test_user.id,
            parent_id=parent_comment.id,
            tenant_id=test_firm.id,
        )
        db_session.add(reply)
        await db_session.flush()
        await db_session.refresh(reply)

        assert reply.parent_id == parent_comment.id
        assert reply.content == "Reply to parent"

    @pytest.mark.integration
    async def test_create_internal_note(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        internal_note = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.INTERNAL_NOTE,
            content="Internal note for team",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(internal_note)
        await db_session.flush()
        await db_session.refresh(internal_note)

        assert internal_note.comment_type == CommentType.INTERNAL_NOTE

    @pytest.mark.integration
    async def test_create_comment_attachment(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        comment = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="Comment with attachment",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(comment)
        await db_session.flush()

        attachment = CommentAttachment(
            comment_id=comment.id,
            filename="document.pdf",
            original_filename="document.pdf",
            file_size=1024,
            mime_type="application/pdf",
            storage_path="path/to/document.pdf",
            storage_key="key123",
            uploaded_by=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(attachment)
        await db_session.flush()
        await db_session.refresh(attachment)

        assert attachment.id is not None
        assert attachment.comment_id == comment.id

    @pytest.mark.integration
    async def test_create_comment_reaction(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        comment = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="Comment for reaction",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(comment)
        await db_session.flush()

        reaction = CommentReaction(
            comment_id=comment.id,
            user_id=test_user.id,
            reaction_type="like",
            tenant_id=test_firm.id,
        )
        db_session.add(reaction)
        await db_session.flush()
        await db_session.refresh(reaction)

        assert reaction.id is not None
        assert reaction.reaction_type == "like"
        assert reaction.comment_id == comment.id

    @pytest.mark.integration
    async def test_unique_reaction_per_user(self, db_session: AsyncSession, test_firm: Firm, test_user: User, test_matter: Matter):
        from sqlalchemy.exc import IntegrityError

        comment = Comment(
            entity_type="matter",
            entity_id=test_matter.id,
            comment_type=CommentType.COMMENT,
            content="Comment for unique reaction test",
            author_id=test_user.id,
            tenant_id=test_firm.id,
        )
        db_session.add(comment)
        await db_session.flush()

        reaction1 = CommentReaction(
            comment_id=comment.id,
            user_id=test_user.id,
            reaction_type="like",
            tenant_id=test_firm.id,
        )
        db_session.add(reaction1)
        await db_session.flush()

        # Try to create duplicate reaction
        reaction2 = CommentReaction(
            comment_id=comment.id,
            user_id=test_user.id,
            reaction_type="like",
            tenant_id=test_firm.id,
        )
        db_session.add(reaction2)

        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestCollaborationTenantIsolation:
    """Tests for Collaboration tenant isolation."""

    @pytest.mark.integration
    async def test_comment_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        """Test that comments are isolated by tenant."""
        from sqlalchemy import text

        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create users
        user_a = User(email="usera@firm-a.com", hashed_password="hashed", full_name="User A", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        user_b = User(email="userb@firm-b.com", hashed_password="hashed", full_name="User B", tenant_id=other_firm.id, roles=["associate"], is_active=True)
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        # Create clients and matters
        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=user_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=other_firm.id, responsible_user_id=user_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        matter_a = Matter(name="Matter A", matter_type="TAX", status="IN_PROGRESS", client_id=client_a.id, responsible_user_id=user_a.id, tenant_id=test_firm.id)
        matter_b = Matter(name="Matter B", matter_type="TAX", status="IN_PROGRESS", client_id=client_b.id, responsible_user_id=user_b.id, tenant_id=other_firm.id)
        db_session.add_all([matter_a, matter_b])
        await db_session.flush()

        # Create comments
        comment_a = Comment(entity_type="matter", entity_id=matter_a.id, comment_type=CommentType.COMMENT, content="Comment A", author_id=user_a.id, tenant_id=test_firm.id)
        comment_b = Comment(entity_type="matter", entity_id=matter_b.id, comment_type=CommentType.COMMENT, content="Comment B", author_id=user_b.id, tenant_id=other_firm.id)
        db_session.add_all([comment_a, comment_b])
        await db_session.flush()

        # Set tenant context to Firm A
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=user_a.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(Comment))
        comments = result.scalars().all()
        assert len(comments) == 1
        assert comments[0].id == comment_a.id

        clear_tenant_context()

        # Set tenant context to Firm B
        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=user_b.id)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(Comment))
        comments = result.scalars().all()
        assert len(comments) == 1
        assert comments[0].id == comment_b.id

        clear_tenant_context()