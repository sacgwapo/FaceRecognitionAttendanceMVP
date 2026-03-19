"""
Face Recognition Attendance System - Main Application

PRIVACY & CONSENT NOTICE:
This application processes biometric data (facial images and embeddings).
Before deploying, ensure you have:
1. Obtained explicit consent from all users whose faces will be registered
2. Informed users about how their biometric data will be stored and used
3. Implemented appropriate data retention and deletion policies
4. Complied with local privacy laws (GDPR, CCPA, etc.)

DATA STORAGE:
- Face embeddings are stored in the database (128-dimensional vectors)
- Original face images are optionally stored in /app/data/faces
- Attendance logs are stored in SQLite database
- Audit logs track all administrative actions
- All data is stored locally - no external cloud services
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.config import get_settings, ensure_directories
from app.database import init_db
from app.utils.logging import setup_logging, get_logger
from app.utils.security import get_current_user, require_role
from app.routers import auth, users, attendance, recognition, export, settings, admin_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger = get_logger()
    logger.info("Starting Face Attendance System...")

    ensure_directories()
    init_db()
    logger.info("Database initialized")

    yield

    logger.info("Shutting down Face Attendance System...")


app_settings = get_settings()

app = FastAPI(
    title=app_settings.APP_NAME,
    version=app_settings.APP_VERSION,
    description="Face Recognition Attendance System for local deployment",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin_users.router)
app.include_router(users.router)
app.include_router(attendance.router)
app.include_router(recognition.router)
app.include_router(export.router)
app.include_router(settings.router)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": app_settings.APP_VERSION}


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: dict = Depends(require_role("admin", "hr", "attendance"))):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, current_user: dict = Depends(require_role("admin", "hr"))):
    return templates.TemplateResponse("users.html", {"request": request})


@app.get("/attendance", response_class=HTMLResponse)
async def attendance_page(request: Request, current_user: dict = Depends(require_role("admin", "hr"))):
    return templates.TemplateResponse("attendance.html", {"request": request})


@app.get("/recognition", response_class=HTMLResponse)
async def recognition_page(request: Request, current_user: dict = Depends(require_role("admin", "hr", "attendance"))):
    return templates.TemplateResponse("recognition.html", {"request": request})


@app.get("/exports", response_class=HTMLResponse)
async def exports_page(request: Request, current_user: dict = Depends(require_role("admin", "hr"))):
    return templates.TemplateResponse("exports.html", {"request": request})


@app.get("/settings-page", response_class=HTMLResponse)
async def settings_page(request: Request, current_user: dict = Depends(require_role("admin"))):
    return templates.TemplateResponse("settings.html", {"request": request})


@app.get("/hr-dashboard", response_class=HTMLResponse)
async def hr_dashboard_page(request: Request, current_user: dict = Depends(require_role("admin", "hr"))):
    return templates.TemplateResponse("hr_dashboard.html", {"request": request})


@app.get("/admin-accounts", response_class=HTMLResponse)
async def admin_accounts_page(request: Request, current_user: dict = Depends(require_role("admin"))):
    return templates.TemplateResponse("admin_accounts.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
