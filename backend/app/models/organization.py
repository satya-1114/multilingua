from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import BaseMixin


class Organization(BaseMixin, Base):
    __tablename__ = "organizations"
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(60), nullable=False, default="Enterprise")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
