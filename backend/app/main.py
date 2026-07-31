from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import admin_router, chat_router, knowledge_router, sessions_router
from .core.config import settings
from .core.exceptions import AppException
from .core.logger import setup_logger
from .core.tenant import TenantMiddleware

setup_logger(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .core.database import init_db
    from .proactive.scanner import ProactiveScanner

    await init_db()

    scanner = ProactiveScanner()
    await scanner.start()
    app.state.scanner = scanner
    yield
    await scanner.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
if settings.tenant_mode == "multi":
    app.add_middleware(TenantMiddleware)
app.include_router(chat_router, prefix="")
app.include_router(sessions_router, prefix="")
app.include_router(admin_router, prefix="")
app.include_router(knowledge_router, prefix="")


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "db": "connected"}
