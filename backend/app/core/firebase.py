import json
import logging
import firebase_admin
from firebase_admin import credentials

logger = logging.getLogger(__name__)
_app: firebase_admin.App | None = None


def get_firebase_app() -> firebase_admin.App | None:
    global _app
    if _app is not None:
        return _app
    if firebase_admin._apps:
        _app = firebase_admin.get_app()
        return _app

    from app.core.config import settings
    if not settings.FIREBASE_SERVICE_ACCOUNT:
        logger.warning("FIREBASE_SERVICE_ACCOUNT not set — Firebase auth disabled")
        return None

    try:
        cred_dict = json.loads(settings.FIREBASE_SERVICE_ACCOUNT)
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")
        return _app
    except Exception as exc:
        logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
        return None
