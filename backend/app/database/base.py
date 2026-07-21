from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Root ORM base class. All SQLAlchemy models inherit from this."""


# Eagerly register every ORM model with ``Base.metadata`` so that simply
# importing ``app.database.base`` (as Alembic's env.py, seed scripts, and
# tests do) is enough to populate the metadata. Import is placed at the
# bottom of the module — after ``Base`` is defined — so that model modules
# doing ``from app.database.base import Base`` resolve correctly against
# the partially-initialised module.
from app import models as _models  # noqa: E402,F401
