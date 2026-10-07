from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings

router = APIRouter(tags=["health"])


def get_db():
    """Placeholder for database dependency - will be properly implemented in Phase 2"""
    # For now, return None - health check won't test DB
    return None


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "database": "not_configured"
    }

    if db is not None:
        try:
            db.execute(text("SELECT 1"))
            health_status["database"] = "connected"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["database"] = f"error: {str(e)}"

    return health_status