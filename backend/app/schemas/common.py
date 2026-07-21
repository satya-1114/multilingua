from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class IdentifiedDto(ORMModel):
    id: uuid.UUID
    createdAt: datetime
    updatedAt: datetime

    @classmethod
    def model_validate_orm(cls, obj):
        return cls.model_validate({
            "id": obj.id,
            "createdAt": obj.created_at,
            "updatedAt": obj.updated_at,
            **{k: getattr(obj, k) for k in cls.model_fields if k not in {"id", "createdAt", "updatedAt"} and hasattr(obj, k)},
        })
