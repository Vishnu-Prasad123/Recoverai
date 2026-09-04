from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Health Check"])

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    System Health Check Endpoint.
    Verifies service status, database connectivity, and environment metadata.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"disconnected: {str(e)}"

    return {
        "status": "healthy" if "connected" in db_status else "degraded",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": {
            "status": db_status,
            "type": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
        },
        "razorpay_integration": {
            "configured": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET)
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
