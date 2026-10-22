from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import AppException, app_exception_handler, general_exception_handler
from app.core.logging import RequestIDMiddleware, setup_logging
from app.routers import chat, health, properties

# Setup logging
setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
    description="AI-powered Real Estate Agent API",
)

# Middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Routers
app.include_router(health.router)
app.include_router(properties.router)
app.include_router(chat.router)  # NEW: Phase 4 Chat API


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    # Register all agent tools
    from app.agent.registry import register_all_tools
    register_all_tools()
    
    print("✅ AI Agent tools registered")
    print(f"✅ {settings.APP_NAME} started successfully")


# Root endpoint
@app.get("/")
def read_root():
    """API root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "phase": "4 - AI Agent & Chat API",
    }