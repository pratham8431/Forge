"""
Run once at startup or via: python -m app.iam.access.seed
Seeds all roles and permissions into the database.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.iam.identity.models import Role, Permission, RolePermission

PERMISSIONS = [
    ("review:create",    "Submit code for AI review"),
    ("review:read",      "View code review results"),
    ("review:delete",    "Delete code review records"),
    ("incident:read",    "View incident reports"),
    ("incident:analyze", "Run AI incident analysis"),
    ("sql:execute",      "Execute AI-generated SQL"),
    ("sql:read",         "View SQL query history"),
    ("docs:generate",    "Generate documentation"),
    ("docs:read",        "Read documentation"),
    ("rag:search",       "Search internal knowledge base"),
    ("api:explore",      "Use API Explorer"),
    ("analytics:read",   "View analytics dashboards"),
    ("admin:users",      "Manage users"),
    ("admin:roles",      "Manage roles and permissions"),
    ("admin:sessions",   "View and revoke all sessions"),
]

ROLES: dict[str, list[str]] = {
    "admin": [p[0] for p in PERMISSIONS],
    "developer": [
        "review:create", "review:read",
        "sql:execute", "sql:read",
        "docs:read", "rag:search", "api:explore",
    ],
    "manager": [
        "review:read", "analytics:read",
        "incident:read", "rag:search", "docs:read",
    ],
    "qa": [
        "review:create", "review:read",
        "docs:generate", "docs:read", "rag:search",
    ],
    "devops": [
        "incident:read", "incident:analyze",
        "sql:execute", "sql:read", "analytics:read",
    ],
}


async def seed():
    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        # Upsert permissions
        perm_map: dict[str, Permission] = {}
        for name, desc in PERMISSIONS:
            result = await db.execute(select(Permission).where(Permission.name == name))
            perm = result.scalar_one_or_none()
            if not perm:
                perm = Permission(name=name, description=desc)
                db.add(perm)
                await db.flush()
            perm_map[name] = perm

        # Upsert roles and wire permissions
        for role_name, perm_names in ROLES.items():
            result = await db.execute(select(Role).where(Role.name == role_name))
            role = result.scalar_one_or_none()
            if not role:
                role = Role(name=role_name, description=f"{role_name.capitalize()} role")
                db.add(role)
                await db.flush()

            existing_perms = {p.name for p in role.permissions} if role.permissions else set()
            for pname in perm_names:
                if pname not in existing_perms:
                    role.permissions.append(perm_map[pname])

        await db.commit()
        print("Seed complete: roles and permissions inserted.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
