import time, uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.database import Base, engine
from app.api.v1 import auth, complaints, dashboard, uploads
import app.models
Base.metadata.create_all(bind=engine)  # Alembic owns production schema changes.
app = FastAPI(title="Rail Madad AI Backend", version="0.1.0", description="AI-ready, AI-independent complaint management API")
settings = get_settings(); settings.local_storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.local_storage_path), name="media")
@app.middleware("http")
async def request_context(request: Request, call_next):
    start=time.perf_counter(); request_id=str(uuid.uuid4())
    try: response=await call_next(request)
    except Exception: return JSONResponse(status_code=500, content={"success":False,"error":{"code":"INTERNAL_ERROR","message":"An unexpected error occurred."}})
    response.headers["X-Request-ID"] = request_id; response.headers["X-Response-Time-Ms"] = str(round((time.perf_counter()-start)*1000, 2)); return response
@app.exception_handler(HTTPException)
async def api_http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": {"code": "REQUEST_ERROR", "message": str(exc.detail)}})
@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Request validation failed.", "details": exc.errors()}})
@app.get("/api/v1/health", tags=["Health"])
def health(): return {"status":"ok"}
app.include_router(auth.router, prefix="/api/v1")
app.include_router(uploads.router, prefix="/api/v1")
app.include_router(complaints.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
