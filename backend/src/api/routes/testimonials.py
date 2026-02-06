"""Testimonials endpoints.

Public endpoints for fetching approved user testimonials.
"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from src.db.database import get_session
from src.db.models import Testimonial

logger = logging.getLogger(__name__)

router = APIRouter()


class TestimonialResponse(BaseModel):
    """Single testimonial response."""

    id: int
    author_name: str
    author_role: str | None = None
    content: str
    rating: int
    avatar_url: str | None = None
    created_at: str


class TestimonialListResponse(BaseModel):
    """List of testimonials response."""

    testimonials: list[TestimonialResponse]
    count: int


@router.get("", response_model=TestimonialListResponse)
async def get_testimonials() -> TestimonialListResponse:
    """
    Get approved testimonials.

    Returns up to 6 most recent approved testimonials.
    No authentication required (public endpoint).
    """
    async with get_session() as session:
        stmt = (
            select(Testimonial)
            .where(Testimonial.is_approved.is_(True))
            .order_by(Testimonial.created_at.desc())
            .limit(6)
        )
        result = await session.execute(stmt)
        testimonials = result.scalars().all()

    items = [
        TestimonialResponse(
            id=t.id,
            author_name=t.author_name,
            author_role=t.author_role,
            content=t.content,
            rating=t.rating,
            avatar_url=t.avatar_url,
            created_at=t.created_at.isoformat(),
        )
        for t in testimonials
    ]

    return TestimonialListResponse(testimonials=items, count=len(items))
