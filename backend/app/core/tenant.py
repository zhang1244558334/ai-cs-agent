from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "missing_tenant", "message": "X-Tenant-ID header is required"}},
            )
        request.state.tenant_id = tenant_id
        return await call_next(request)


def get_current_tenant(request: Request) -> str:
    return request.state.tenant_id
