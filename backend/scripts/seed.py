"""Development seed script — creates baseline roles and a super admin."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.session import SessionLocal  # noqa: E402
from app.models.user import Role, User, UserRole  # noqa: E402
from app.security.passwords import hash_password  # noqa: E402


ROLES = [
    ("super_admin", "Full platform access"),
    ("org_admin", "Organization administrator"),
    ("campaign_manager", "Plans and launches campaigns"),
    ("content_creator", "Drafts campaign content"),
    ("communication_officer", "Coordinates delivery"),
    ("data_analyst", "Reads analytics and reports"),
    ("viewer", "Read-only access"),
    ("volunteer", "Field volunteer — acts on assigned tasks"),
    ("translator", "Translates content across supported locales"),
    ("reviewer", "Reviews and publishes translated content"),
]


def main() -> None:
    db = SessionLocal()
    try:
        role_map = {}
        for name, desc in ROLES:
            role = db.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.add(role)
                db.flush()
            role_map[name] = role

        admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("SEED_ADMIN_PASSWORD", "ChangeMe123!")
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                full_name="Platform Administrator",
                hashed_password=hash_password(admin_password),
                is_active=True,
            )
            db.add(admin)
            db.flush()
            db.add(UserRole(user_id=admin.id, role_id=role_map["super_admin"].id))
        db.commit()
        print(f"Seed complete. Admin: {admin_email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
