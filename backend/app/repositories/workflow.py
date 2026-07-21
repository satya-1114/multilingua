"""Repository layer for the Automation & Workflow Engine (Phase 7.2).

Thin extensions over :class:`CRUDBase`. All business rules — transition
validation, uniqueness, ordering — live in :mod:`app.services.workflow`.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.workflow import (
    WorkflowAction,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTrigger,
)


# --------------------------------------------------------------------------- #
# WorkflowDefinition
# --------------------------------------------------------------------------- #


class WorkflowDefinitionRepository(CRUDBase[WorkflowDefinition]):
    def __init__(self) -> None:
        super().__init__(WorkflowDefinition)

    def create_definition(self, db: Session, data: dict[str, Any]) -> WorkflowDefinition:
        return self.create(db, data)

    def get_definition(
        self, db: Session, definition_id: uuid.UUID | str
    ) -> WorkflowDefinition | None:
        return self.get(db, definition_id)

    def find_by_name(
        self,
        db: Session,
        *,
        name: str,
        organization_id: uuid.UUID | str | None,
    ) -> WorkflowDefinition | None:
        stmt = select(WorkflowDefinition).where(
            WorkflowDefinition.deleted_at.is_(None),
            WorkflowDefinition.name == name,
        )
        if organization_id is None:
            stmt = stmt.where(WorkflowDefinition.organization_id.is_(None))
        else:
            stmt = stmt.where(WorkflowDefinition.organization_id == organization_id)
        return db.scalar(stmt)

    def list_definitions(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        query: str | None = None,
        trigger_type: str | None = None,
        enabled: bool | None = None,
        organization_id: uuid.UUID | str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[WorkflowDefinition], int]:
        stmt = select(WorkflowDefinition).where(WorkflowDefinition.deleted_at.is_(None))
        if trigger_type:
            stmt = stmt.where(WorkflowDefinition.trigger_type == trigger_type)
        if enabled is not None:
            stmt = stmt.where(WorkflowDefinition.enabled == enabled)
        if organization_id is not None:
            stmt = stmt.where(WorkflowDefinition.organization_id == organization_id)
        if created_from:
            stmt = stmt.where(WorkflowDefinition.created_at >= created_from)
        if created_to:
            stmt = stmt.where(WorkflowDefinition.created_at <= created_to)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(
                    WorkflowDefinition.name.ilike(like),
                    WorkflowDefinition.description.ilike(like),
                )
            )
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(WorkflowDefinition, sort_by):
            col = getattr(WorkflowDefinition, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(WorkflowDefinition.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_definition(
        self, db: Session, obj: WorkflowDefinition, data: dict[str, Any]
    ) -> WorkflowDefinition:
        return self.update(db, obj, data)

    def delete_definition(self, db: Session, obj: WorkflowDefinition) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# WorkflowTrigger
# --------------------------------------------------------------------------- #


class WorkflowTriggerRepository(CRUDBase[WorkflowTrigger]):
    def __init__(self) -> None:
        super().__init__(WorkflowTrigger)

    def create_trigger(self, db: Session, data: dict[str, Any]) -> WorkflowTrigger:
        return self.create(db, data)

    def get_trigger(
        self, db: Session, trigger_id: uuid.UUID | str
    ) -> WorkflowTrigger | None:
        return self.get(db, trigger_id)

    def list_triggers(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        workflow_definition_id: uuid.UUID | str | None = None,
        event_name: str | None = None,
        event_source: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[WorkflowTrigger], int]:
        stmt = select(WorkflowTrigger).where(WorkflowTrigger.deleted_at.is_(None))
        if workflow_definition_id is not None:
            stmt = stmt.where(
                WorkflowTrigger.workflow_definition_id == workflow_definition_id
            )
        if event_name:
            stmt = stmt.where(WorkflowTrigger.event_name == event_name)
        if event_source:
            stmt = stmt.where(WorkflowTrigger.event_source == event_source)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(WorkflowTrigger, sort_by):
            col = getattr(WorkflowTrigger, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(WorkflowTrigger.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_trigger(
        self, db: Session, obj: WorkflowTrigger, data: dict[str, Any]
    ) -> WorkflowTrigger:
        return self.update(db, obj, data)

    def delete_trigger(self, db: Session, obj: WorkflowTrigger) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# WorkflowAction
# --------------------------------------------------------------------------- #


class WorkflowActionRepository(CRUDBase[WorkflowAction]):
    def __init__(self) -> None:
        super().__init__(WorkflowAction)

    def create_action(self, db: Session, data: dict[str, Any]) -> WorkflowAction:
        return self.create(db, data)

    def get_action(
        self, db: Session, action_id: uuid.UUID | str
    ) -> WorkflowAction | None:
        return self.get(db, action_id)

    def list_actions(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        workflow_definition_id: uuid.UUID | str | None = None,
        action_type: str | None = None,
        enabled: bool | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> tuple[list[WorkflowAction], int]:
        stmt = select(WorkflowAction).where(WorkflowAction.deleted_at.is_(None))
        if workflow_definition_id is not None:
            stmt = stmt.where(
                WorkflowAction.workflow_definition_id == workflow_definition_id
            )
        if action_type:
            stmt = stmt.where(WorkflowAction.action_type == action_type)
        if enabled is not None:
            stmt = stmt.where(WorkflowAction.enabled == enabled)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(WorkflowAction, sort_by):
            col = getattr(WorkflowAction, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(WorkflowAction.sequence.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def ordered_actions(
        self, db: Session, workflow_definition_id: uuid.UUID | str
    ) -> list[WorkflowAction]:
        stmt = (
            select(WorkflowAction)
            .where(
                WorkflowAction.deleted_at.is_(None),
                WorkflowAction.workflow_definition_id == workflow_definition_id,
            )
            .order_by(WorkflowAction.sequence.asc())
        )
        return list(db.scalars(stmt))

    def find_by_sequence(
        self,
        db: Session,
        *,
        workflow_definition_id: uuid.UUID | str,
        sequence: int,
    ) -> WorkflowAction | None:
        stmt = select(WorkflowAction).where(
            WorkflowAction.deleted_at.is_(None),
            WorkflowAction.workflow_definition_id == workflow_definition_id,
            WorkflowAction.sequence == sequence,
        )
        return db.scalar(stmt)

    def update_action(
        self, db: Session, obj: WorkflowAction, data: dict[str, Any]
    ) -> WorkflowAction:
        return self.update(db, obj, data)

    def delete_action(self, db: Session, obj: WorkflowAction) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# WorkflowExecution
# --------------------------------------------------------------------------- #


class WorkflowExecutionRepository(CRUDBase[WorkflowExecution]):
    def __init__(self) -> None:
        super().__init__(WorkflowExecution)

    def create_execution(self, db: Session, data: dict[str, Any]) -> WorkflowExecution:
        return self.create(db, data)

    def get_execution(
        self, db: Session, execution_id: uuid.UUID | str
    ) -> WorkflowExecution | None:
        return self.get(db, execution_id)

    def list_executions(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        workflow_definition_id: uuid.UUID | str | None = None,
        status: str | None = None,
        trigger_event: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        sort_by: str | None = None,
        sort_dir: str = "desc",
    ) -> tuple[list[WorkflowExecution], int]:
        stmt = select(WorkflowExecution).where(WorkflowExecution.deleted_at.is_(None))
        if workflow_definition_id is not None:
            stmt = stmt.where(
                WorkflowExecution.workflow_definition_id == workflow_definition_id
            )
        if status:
            stmt = stmt.where(WorkflowExecution.status == status)
        if trigger_event:
            stmt = stmt.where(WorkflowExecution.trigger_event == trigger_event)
        if started_from:
            stmt = stmt.where(WorkflowExecution.started_at >= started_from)
        if started_to:
            stmt = stmt.where(WorkflowExecution.started_at <= started_to)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(WorkflowExecution, sort_by):
            col = getattr(WorkflowExecution, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(WorkflowExecution.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_execution(
        self, db: Session, obj: WorkflowExecution, data: dict[str, Any]
    ) -> WorkflowExecution:
        return self.update(db, obj, data)

    def delete_execution(self, db: Session, obj: WorkflowExecution) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# WorkflowExecutionStep
# --------------------------------------------------------------------------- #


class WorkflowExecutionStepRepository(CRUDBase[WorkflowExecutionStep]):
    def __init__(self) -> None:
        super().__init__(WorkflowExecutionStep)

    def create_step(
        self, db: Session, data: dict[str, Any]
    ) -> WorkflowExecutionStep:
        return self.create(db, data)

    def get_step(
        self, db: Session, step_id: uuid.UUID | str
    ) -> WorkflowExecutionStep | None:
        return self.get(db, step_id)

    def list_steps(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 50,
        workflow_execution_id: uuid.UUID | str | None = None,
        workflow_action_id: uuid.UUID | str | None = None,
        status: str | None = None,
        sort_by: str | None = None,
        sort_dir: str = "asc",
    ) -> tuple[list[WorkflowExecutionStep], int]:
        stmt = select(WorkflowExecutionStep).where(
            WorkflowExecutionStep.deleted_at.is_(None)
        )
        if workflow_execution_id is not None:
            stmt = stmt.where(
                WorkflowExecutionStep.workflow_execution_id == workflow_execution_id
            )
        if workflow_action_id is not None:
            stmt = stmt.where(
                WorkflowExecutionStep.workflow_action_id == workflow_action_id
            )
        if status:
            stmt = stmt.where(WorkflowExecutionStep.status == status)
        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        if sort_by and hasattr(WorkflowExecutionStep, sort_by):
            col = getattr(WorkflowExecutionStep, sort_by)
            stmt = stmt.order_by(col.desc() if sort_dir == "desc" else col.asc())
        else:
            stmt = stmt.order_by(WorkflowExecutionStep.created_at.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        return list(db.scalars(stmt)), int(total)

    def update_step(
        self, db: Session, obj: WorkflowExecutionStep, data: dict[str, Any]
    ) -> WorkflowExecutionStep:
        return self.update(db, obj, data)

    def delete_step(self, db: Session, obj: WorkflowExecutionStep) -> None:
        self.soft_delete(db, obj)


# --------------------------------------------------------------------------- #
# Module-level singletons
# --------------------------------------------------------------------------- #

workflow_definitions = WorkflowDefinitionRepository()
workflow_triggers = WorkflowTriggerRepository()
workflow_actions = WorkflowActionRepository()
workflow_executions = WorkflowExecutionRepository()
workflow_execution_steps = WorkflowExecutionStepRepository()


__all__ = [
    "WorkflowDefinitionRepository",
    "WorkflowTriggerRepository",
    "WorkflowActionRepository",
    "WorkflowExecutionRepository",
    "WorkflowExecutionStepRepository",
    "workflow_definitions",
    "workflow_triggers",
    "workflow_actions",
    "workflow_executions",
    "workflow_execution_steps",
]
