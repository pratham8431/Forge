import uuid
from app.workers.celery_app import celery_app


@celery_app.task(name="audit.log_event", bind=True, max_retries=3)
def log_audit_event(
    self,
    user_id: str | None,
    action: str,
    ip_address: str | None = None,
    resource: str | None = None,
    metadata: dict | None = None,
):
    """
    Async audit logger — never called synchronously from auth endpoints.
    Writes to audit_logs table. Retries up to 3 times on DB failure.
    """
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from app.core.config import settings
        from app.iam.identity.models import AuditLog, AuditAction

        engine = create_async_engine(settings.DATABASE_URL)
        SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async def _write():
            async with SessionLocal() as session:
                log = AuditLog(
                    user_id=uuid.UUID(user_id) if user_id else None,
                    action=AuditAction(action),
                    ip_address=ip_address,
                    resource=resource,
                    metadata=metadata,
                )
                session.add(log)
                await session.commit()
            await engine.dispose()

        asyncio.run(_write())

    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)
