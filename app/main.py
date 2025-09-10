import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlmodel import SQLModel

from .api.auth import router as auth_router
from .api.contract import router as contract_router
from .api.organizations import router as org_router
from .api.signatures import router as signatures_router
from .api.templates import router as templates_router
from .api.users import router as user_router
from .core.database import engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 ContractFlow API starting up...")
    create_db_and_tables()
    logger.info("✅ Database tables created/verified")
    yield
    # Shutdown
    logger.info("👋 ContractFlow API shutting down...")


app = FastAPI(
    title="ContractFlow API", 
    description="Professional Contract Management System with advanced features",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173', 'http://localhost:3000'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/api/health", tags=['Health Check'])
async def health_check():
    return {"status": "ok", "message": "ContractFlow API is running"}

app.include_router(auth_router, prefix='/api/auth', tags=['Authentication'])
app.include_router(user_router, prefix='/api/users', tags=['Users'])
app.include_router(org_router, prefix='/api/organizations', tags=['Admin Organizations'])
app.include_router(contract_router, prefix='/api/contracts', tags=['Contracts'])
app.include_router(signatures_router, prefix='/api/contracts', tags=['Contract Signatures'])
app.include_router(templates_router, prefix='/api/templates', tags=['Contract Templates'])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
