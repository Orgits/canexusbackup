# Reviews CRUD Integration Tests

import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, date

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.reviews.models import ReviewRequest, ReviewComment, ReviewHistory, ReviewStage, ReviewStatus
from app.modules.firms.models import Firm
from app.modules.users.models import User
from app.modules.clients.models import Client
from app.modules.matters.models import Matter, MatterType, MatterStatus, MatterPriority
from app.core.security import hash_password
from app.core.tenancy.context import TenantContext, set_tenant_context, clear_tenant_context


class TestReviewsCRUD:
    """Tests for Reviews CRUD operations."""

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
    async def test_reviewer(self, db_session: AsyncSession, test_firm: Firm) -> User:
        user = User(
            email="reviewer@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Reviewer User",
            tenant_id=test_firm.id,
            roles=["senior_associate"],
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
    async def test_create_review_request(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.DRAFT,
            status=ReviewStatus.PENDING,
            reviewer_id=test_reviewer.id,
            reviewer_team_id=None,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()
        await db_session.refresh(review)

        assert review.id is not None
        assert review.source_object_type == "matter"
        assert review.source_object_id == test_matter.id
        assert review.stage == ReviewStage.DRAFT
        assert review.status == ReviewStatus.PENDING
        assert review.reviewer_id == test_reviewer.id

    @pytest.mark.integration
    async def test_review_request_actions(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.DRAFT,
            status=ReviewStatus.PENDING,
            reviewer_id=test_reviewer.id,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()

        # Submit for review
        review.stage = ReviewStage.SUBMITTED
        review.status = ReviewStatus.IN_PROGRESS
        review.submitted_at = datetime.now()
        await db_session.flush()

        assert review.stage == ReviewStage.SUBMITTED
        assert review.status == ReviewStatus.IN_PROGRESS

        # Approve
        review.stage = ReviewStage.APPROVED
        review.status = ReviewStatus.COMPLETED
        review.reviewed_at = datetime.now()
        review.reviewed_by_id = test_reviewer.id
        await db_session.flush()

        assert review.stage == ReviewStage.APPROVED
        assert review.status == ReviewStatus.COMPLETED

    @pytest.mark.integration
    async def test_review_rejection(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.SUBMITTED,
            status=ReviewStatus.IN_PROGRESS,
            reviewer_id=test_reviewer.id,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()

        # Reject
        review.stage = ReviewStage.REJECTED
        review.status = ReviewStatus.COMPLETED
        review.reviewed_at = datetime.now()
        review.reviewed_by_id = test_reviewer.id
        review.rejection_reason = "Does not meet compliance requirements"
        await db_session.flush()

        assert review.stage == ReviewStage.REJECTED
        assert review.rejection_reason == "Does not meet compliance requirements"

    @pytest.mark.integration
    async def test_review_rework(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.SUBMITTED,
            status=ReviewStatus.IN_PROGRESS,
            reviewer_id=test_reviewer.id,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()

        # Request rework
        review.stage = ReviewStage.REWORK
        review.status = ReviewStatus.IN_PROGRESS
        review.rework_comments = "Please fix the calculations in section 3"
        await db_session.flush()

        assert review.stage == ReviewStage.REWORK
        assert review.rework_comments == "Please fix the calculations in section 3"

        # Resubmit after rework
        review.stage = ReviewStage.SUBMITTED
        review.status = ReviewStatus.IN_PROGRESS
        review.submitted_at = datetime.now()
        await db_session.flush()

        assert review.stage == ReviewStage.SUBMITTED

    @pytest.mark.integration
    async def test_create_review_comment(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.SUBMITTED,
            status=ReviewStatus.IN_PROGRESS,
            reviewer_id=test_reviewer.id,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()

        # Add comment from reviewer
        comment = ReviewComment(
            review_request_id=review.id,
            author_id=test_reviewer.id,
            content="Please clarify the tax calculation in section 2",
            comment_type="reviewer_comment",
            is_internal=False,
            tenant_id=test_firm.id,
        )
        db_session.add(comment)
        await db_session.flush()
        await db_session.refresh(comment)

        assert comment.id is not None
        assert comment.review_request_id == review.id
        assert comment.author_id == test_reviewer.id

        # Add reply from submitter
        reply = ReviewComment(
            review_request_id=review.id,
            author_id=test_user.id,
            content="Updated the calculations as requested",
            comment_type="submitter_response",
            parent_id=comment.id,
            is_internal=False,
            tenant_id=test_firm.id,
        )
        db_session.add(reply)
        await db_session.flush()

        assert reply.parent_id == comment.id
        assert reply.content == "Updated the calculations as requested"

    @pytest.mark.integration
    async def test_review_history_tracking(self, db_session: AsyncSession, test_firm: Firm, test_matter: Matter, test_user: User, test_reviewer: User):
        review = ReviewRequest(
            source_object_type="matter",
            source_object_id=test_matter.id,
            stage=ReviewStage.DRAFT,
            status=ReviewStatus.PENDING,
            reviewer_id=test_reviewer.id,
            submitted_by_id=test_user.id,
            due_date=date(2025, 2, 15),
            tenant_id=test_firm.id,
        )
        db_session.add(review)
        await db_session.flush()

        # Create history entries
        history1 = ReviewHistory(
            review_request_id=review.id,
            actor_id=test_user.id,
            action="SUBMITTED",
            from_stage=ReviewStage.DRAFT,
            to_stage=ReviewStage.SUBMITTED,
            from_status=ReviewStatus.PENDING,
            to_status=ReviewStatus.IN_PROGRESS,
            comment="Submitted for review",
            tenant_id=test_firm.id,
        )
        db_session.add(history1)
        await db_session.flush()

        history2 = ReviewHistory(
            review_request_id=review.id,
            actor_id=test_reviewer.id,
            action="APPROVED",
            from_stage=ReviewStage.SUBMITTED,
            to_stage=ReviewStage.APPROVED,
            from_status=ReviewStatus.IN_PROGRESS,
            to_status=ReviewStatus.COMPLETED,
            comment="Approved after review",
            tenant_id=test_firm.id,
        )
        db_session.add(history2)
        await db_session.flush()

        # Query history
        result = await db_session.execute(
            select(ReviewHistory)
            .where(ReviewHistory.review_request_id == review.id)
            .order_by(ReviewHistory.created_at)
        )
        history = result.scalars().all()

        assert len(history) == 2
        assert history[0].action == "SUBMITTED"
        assert history[1].action == "APPROVED"


class TestReviewsTenantIsolation:
    """Tests for Reviews tenant isolation."""

    @pytest.mark.integration
    async def test_review_tenant_isolation(
        self, db_session: AsyncSession, test_firm: Firm
    ):
        from sqlalchemy import text

        # Create second firm
        other_firm = Firm(name="Other Firm", is_active=True, settings={}, country="India")
        db_session.add(other_firm)
        await db_session.flush()

        # Create users and matters
        user_a = User(email="usera@firm-a.com", hashed_password="hashed", full_name="User A", tenant_id=test_firm.id, roles=["associate"], is_active=True)
        user_b = User(email="userb@firm-b.com", hashed_password="hashed", full_name="User B", tenant_id=other_firm.id, roles=["associate"], is_active=True)
        db_session.add_all([user_a, user_b])
        await db_session.flush()

        client_a = Client(name="Client A", category="COMPANY", status="ACTIVE", tenant_id=test_firm.id, responsible_user_id=user_a.id)
        client_b = Client(name="Client B", category="COMPANY", status="ACTIVE", tenant_id=other_firm.id, responsible_user_id=user_b.id)
        db_session.add_all([client_a, client_b])
        await db_session.flush()

        matter_a = Matter(name="Matter A", matter_type="TAX", status="IN_PROGRESS", client_id=client_a.id, responsible_user_id=user_a.id, tenant_id=test_firm.id)
        matter_b = Matter(name="Matter B", matter_type="TAX", status="IN_PROGRESS", client_id=client_b.id, responsible_user_id=user_b.id, tenant_id=other_firm.id)
        db_session.add_all([matter_a, matter_b])
        await db_session.flush()

        # Create review requests
        review_a = ReviewRequest(source_object_type="matter", source_object_id=matter_a.id, stage=ReviewStage.DRAFT, status=ReviewStatus.PENDING, submitted_by_id=user_a.id, due_date=date(2025, 2, 15), tenant_id=test_firm.id)
        review_b = ReviewRequest(source_object_type="matter", source_object_id=matter_b.id, stage=ReviewStage.DRAFT, status=ReviewStatus.PENDING, submitted_by_id=user_b.id, due_date=date(2025, 2, 15), tenant_id=other_firm.id)
        db_session.add_all([review_a, review_b])
        await db_session.flush()

        # Test isolation
        context = TenantContext(tenant_id=test_firm.id, firm=test_firm, user_id=None)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{test_firm.id}'"))

        result = await db_session.execute(select(ReviewRequest))
        reviews = result.scalars().all()
        assert len(reviews) == 1
        assert reviews[0].id == review_a.id

        clear_tenant_context()

        context = TenantContext(tenant_id=other_firm.id, firm=other_firm, user_id=None)
        set_tenant_context(context)
        await db_session.execute(text(f"SET LOCAL app.current_tenant = '{other_firm.id}'"))

        result = await db_session.execute(select(ReviewRequest))
        reviews = result.scalars().all()
        assert len(reviews) == 1
        assert reviews[0].id == review_b.id

        clear_tenant_context()