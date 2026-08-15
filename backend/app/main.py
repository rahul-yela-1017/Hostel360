import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import settings
from .database import Base, SessionLocal, engine
from .seed import seed_database
from .routers import admin, auth, kiosk, menu, operations, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
    yield


app = FastAPI(
    title="Smart Hostel Management API",
    version="1.0.0",
    description="Secure role-based API for hostel operations, attendance, mess menu and reporting.",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Kiosk-Key", "X-Request-ID"],
)

# Small in-process guard for sensitive endpoints. Deployments should use Redis/API-gateway limits.
request_windows: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    path = request.url.path
    if path in ("/api/auth/login", "/api/auth/setup/admin", "/api/face/recognize"):
        key = f"{request.client.host if request.client else 'unknown'}:{path}"
        now = time.monotonic(); window = request_windows[key]
        while window and window[0] < now - 60: window.popleft()
        limit = 30 if path.endswith("recognize") else 10
        if len(window) >= limit:
            return JSONResponse(status_code=429, content={"detail": "Too many requests; try again shortly"})
        window.append(now)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
    if settings.app_env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/api/health", tags=["System"])
def health():
    return {"status": "healthy", "service": settings.app_name, "environment": settings.app_env}


for router in (auth.router, admin.router, operations.router, menu.router, reports.router, kiosk.router):
    app.include_router(router, prefix="/api")

# The production image copies the Vite build here so one service can host the SPA and API.
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        requested = (static_dir / full_path).resolve()
        if requested.is_file() and static_dir.resolve() in requested.parents:
            return FileResponse(requested)
        return FileResponse(static_dir / "index.html")
