import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.routes import admin_router, business_router, chat_router, knowledge_router, sessions_router
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

    # 拉平台机器人（从 settings.json 读取持久化的平台配置）
    try:
        from app.platforms.factory import PlatformGateway
        import json as _json, os as _os
        # 优先从持久化配置读
        _settings_file = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "config", "settings.json")
        _persisted = {}
        if _os.path.exists(_settings_file):
            with open(_settings_file) as _f:
                _persisted = _json.load(_f)
        cfg_str = _persisted.get("platform_config", "") or ""
        cfg = _json.loads(cfg_str) if cfg_str else {}
        provider = _persisted.get("platform_provider", "") or settings.platform.provider
        gw = PlatformGateway(provider=provider)

        bots = {
            "xianyu": ("app_key", "app.gateway.adapters.xianyu_bot", "run_xianyu_bot"),
            "taobao": ("app_key", "app.gateway.adapters.taobao_bot", "run_taobao_bot"),
            "jd":     ("app_key", "app.gateway.adapters.jd_bot", "run_jd_bot"),
            "pdd":    ("client_id", "app.gateway.adapters.pdd_bot", "run_pdd_bot"),
        }
        if gw.provider in bots:
            cred_key, mod_path, func_name = bots[gw.provider]
            cred = cfg.get(cred_key, "")
            if cred:
                import importlib
                mod = importlib.import_module(mod_path)
                fn = getattr(mod, func_name)
                app.state.bot_task = asyncio.create_task(fn(cred))
                print(f"[Main] {gw.provider} 机器人已启动")
    except BaseException as e:
        print(f"[Main] 机器人启动失败: {e}")

    # 首次启动灌入商品知识库（延迟执行，等bot连接稳定）
    if _os.environ.get("REINDEX_PRODUCTS", "").lower() == "true":
        async def _deferred_reindex():
            await asyncio.sleep(10)  # 等bot连接稳定
            try:
                cfg2 = cfg if 'cfg' in dir() else {}
                ids_raw = _os.environ.get("REINDEX_ITEM_IDS", "")
                item_ids = [i.strip() for i in ids_raw.split(",") if i.strip()]
                if item_ids and cfg2.get("app_key", ""):
                    from app.gateway.adapters.reindex_products import index_all_known_items
                    print(f"[Main] 开始灌入 {len(item_ids)} 个商品到知识库...")
                    index_all_known_items(item_ids, cfg2.get("app_key", ""))
            except Exception as e:
                print(f"[Main] 商品索引失败: {e}")
        asyncio.create_task(_deferred_reindex())

    yield
    await scanner.stop()
    bot_task = getattr(app.state, "bot_task", None)
    if bot_task:
        bot_task.cancel()


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
app.include_router(business_router, prefix="")


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.app_version, "db": "connected"}
