"""Generic base repository shared by all domain repositories."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id: str) -> ModelT | None:
        return self.db.get(self.model, id)

    def get_or_404(self, id: str) -> ModelT:
        instance = self.get(id)
        if instance is None:
            raise LookupError(f"{self.model.__name__} with id={id} not found")
        return instance

    def list_all(self) -> list[ModelT]:
        return list(self.db.scalars(select(self.model)))

    def add(self, instance: ModelT) -> ModelT:
        self.db.add(instance)
        self.db.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.db.delete(instance)
        self.db.flush()

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, instance: ModelT) -> ModelT:
        self.db.refresh(instance)
        return instance
