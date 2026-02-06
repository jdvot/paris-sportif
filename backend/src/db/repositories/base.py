"""Base repository with generic CRUD operations.

Uses SQLAlchemy 2.0 async patterns with type-safe generics.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Base

# Generic type for model classes
ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository providing common CRUD operations.

    Usage:
        class MatchRepository(BaseRepository[Match]):
            def __init__(self, session: AsyncSession):
                super().__init__(Match, session)
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> ModelT | None:
        """Get a single record by primary key."""
        return cast(ModelT | None, await self.session.get(self.model, id))

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: Any | None = None,
    ) -> Sequence[ModelT]:
        """Get all records with optional pagination."""
        stmt: Select[tuple[ModelT]] = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return cast(Sequence[ModelT], result.scalars().all())

    async def get_by_field(self, field_name: str, value: Any) -> ModelT | None:
        """Get a single record by field value."""
        field = getattr(self.model, field_name)
        stmt = select(self.model).where(field == value)
        result = await self.session.execute(stmt)
        return cast(ModelT | None, result.scalar_one_or_none())

    async def get_many_by_field(
        self,
        field_name: str,
        value: Any,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """Get multiple records by field value."""
        field = getattr(self.model, field_name)
        stmt = select(self.model).where(field == value).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return cast(Sequence[ModelT], result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def create_many(self, items: list[dict[str, Any]]) -> list[ModelT]:
        """Create multiple records."""
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        await self.session.flush()
        for instance in instances:
            await self.session.refresh(instance)
        return instances

    async def update(self, id: int, **kwargs: Any) -> ModelT | None:
        """Update a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_many(
        self,
        filter_field: str,
        filter_value: Any,
        **kwargs: Any,
    ) -> int:
        """Update multiple records matching a filter."""
        field = getattr(self.model, filter_field)
        stmt = update(self.model).where(field == filter_value).values(**kwargs)
        result = await self.session.execute(stmt)
        return cast(int, result.rowcount)

    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def delete_many(self, filter_field: str, filter_value: Any) -> int:
        """Delete multiple records matching a filter."""
        field = getattr(self.model, filter_field)
        stmt = delete(self.model).where(field == filter_value)
        result = await self.session.execute(stmt)
        return cast(int, result.rowcount)

    async def count(self) -> int:
        """Count total records."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return cast(int, result.scalar_one())

    async def exists(self, field_name: str, value: Any) -> bool:
        """Check if a record exists by field value."""
        field = getattr(self.model, field_name)
        stmt = select(func.count()).select_from(self.model).where(field == value)
        result = await self.session.execute(stmt)
        return cast(int, result.scalar_one()) > 0

    async def upsert(self, unique_field: str, unique_value: Any, **kwargs: Any) -> ModelT:
        """Insert or update based on unique field."""
        existing = await self.get_by_field(unique_field, unique_value)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        kwargs[unique_field] = unique_value
        return await self.create(**kwargs)
