import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from infra.logger import logger

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, req: Request, call_next):
        t0 = time.perf_counter()
        resp = await call_next(req)
        ms = (time.perf_counter() - t0) * 1000
        name = getattr(req.scope.get("route"), "name", req.url.path)
        logger.info(f"perf route={name} status={resp.status_code} dur_ms={ms:.1f}")
        return resp