from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.db.models import Feedback, Idea, Innovation, Need, TestSignup

from .schemas import (
    ContactFeedback,
    ContactIdea,
    ContactInnovation,
    ContactNeed,
    ContactProfile,
    ContactSignup,
)


def contact_feedback(feedback: Feedback, innovation: Innovation) -> ContactFeedback:
    need_id = feedback.need_id
    assert need_id is not None
    return ContactFeedback(
        id=feedback.id,
        innovation=ContactInnovation(slug=innovation.slug, title=innovation.title),
        need_id=need_id,
        kind=feedback.kind,
        created_at=feedback.created_at,
    )


async def profile(session: AsyncSession, email: str) -> ContactProfile:
    needs = list(
        (
            await session.exec(
                select(Need)
                .where(func.lower(col(Need.contact_email)) == email)
                .order_by(col(Need.created_at).desc())
            )
        ).all()
    )
    ideas = list(
        (
            await session.exec(
                select(Idea)
                .where(func.lower(col(Idea.contact_email)) == email)
                .order_by(col(Idea.created_at).desc())
            )
        ).all()
    )
    signup_rows = list(
        (
            await session.exec(
                select(TestSignup, Innovation)
                .join(Innovation, col(Innovation.id) == col(TestSignup.innovation_id))
                .where(func.lower(col(TestSignup.contact_email)) == email)
                .order_by(col(TestSignup.created_at).desc())
            )
        ).all()
    )
    feedback_rows = list(
        (
            await session.exec(
                select(Feedback, Innovation)
                .join(Need, col(Need.id) == col(Feedback.need_id))
                .join(Innovation, col(Innovation.id) == col(Feedback.innovation_id))
                .where(func.lower(col(Need.contact_email)) == email)
                .order_by(col(Feedback.created_at).desc())
            )
        ).all()
    )
    return ContactProfile(
        email=email,
        needs=[
            ContactNeed(
                id=need.id,
                number=need.number,
                title=need.title,
                text=need.text,
                status=need.status,
                powiat=need.powiat,
                created_at=need.created_at,
            )
            for need in needs
        ],
        ideas=[
            ContactIdea(
                id=idea.id,
                number=idea.number,
                title=idea.title,
                status=idea.status,
                powiat=idea.powiat,
                created_at=idea.created_at,
            )
            for idea in ideas
        ],
        test_signups=[
            ContactSignup(
                id=signup.id,
                innovation=ContactInnovation(
                    slug=innovation.slug, title=innovation.title
                ),
                who=signup.who,
                organization=signup.organization,
                powiat=signup.powiat,
                note=signup.note,
                status=signup.status,
                created_at=signup.created_at,
            )
            for signup, innovation in signup_rows
        ],
        feedback=[contact_feedback(*row) for row in feedback_rows],
    )
