from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import chat_router, knowledge_router, sessions_router
from .core.config import settings
from .core.exceptions import AppException


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .core.database import init_db

    await init_db()
    yield


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
app.include_router(chat_router, prefix="")
app.include_router(sessions_router, prefix="")
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
