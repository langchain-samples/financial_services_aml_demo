"""FastAPI application main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from app.models import HealthResponse
from app.routes import kyc, aml, load
from app.database import init_db

# Initialize FastAPI app
app = FastAPI(
    title="AML/KYC Financial Services Demo",
    description="Demo showcasing LangSmith integration for AML and KYC processes",
    version="0.1.0",
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    init_db()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(kyc.router)
app.include_router(aml.router)
app.include_router(load.router)

# Import and include reviews router
from app.routes import reviews
app.include_router(reviews.router)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "AML/KYC Financial Services Demo API",
        "version": "0.1.0",
        "endpoints": {
            "kyc": "/kyc/onboard",
            "aml": "/aml/analyze",
            "load_customers": "/load/customers",
            "load_transactions": "/load/transactions",
            "health": "/health",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")
