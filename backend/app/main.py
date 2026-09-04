from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routes import payments, customers, metrics, decisions, guardrails, recovery, webhooks

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="RecoverAI - Autonomous AI Revenue Recovery System for Merchants",
    version=settings.VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(payments.router)
app.include_router(customers.router)
app.include_router(metrics.router)
app.include_router(decisions.router)
app.include_router(guardrails.router)
app.include_router(recovery.router)
app.include_router(webhooks.router)

@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "development",
        "database": {"status": "connected"}
    }
