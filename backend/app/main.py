"""FastAPI ilovasi: API + frontend (statik) bitta konteynerda."""
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import academic, auth, dashboard, grades, notifications, risk, students, users
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def bootstrap_admin() -> None:
    """Baza bo'sh bo'lsa, .env dagi ma'lumotlar bilan birinchi administrator yaratiladi."""
    with SessionLocal() as db:
        if db.scalar(select(func.count(User.id))):
            return
        db.add(User(
            username=settings.admin_username, email=settings.admin_email,
            password_hash=hash_password(settings.admin_password), full_name="Tizim administratori", role="ADMIN",
        ))
        db.commit()
        log.warning("Birinchi administrator yaratildi: %s (parolni darhol almashtiring!)", settings.admin_username)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    bootstrap_admin()
    yield


app = FastAPI(
    title="Talabalar o'zlashtirishini kuzatish va erta ogohlantirish tizimi",
    version="1.0.0",
    description="Baho va davomat asosida xavf guruhidagi talabalarni aniqlovchi REST API.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code,
             (time.perf_counter() - start) * 1000)
    return response


for r in (auth.router, users.router, academic.router, students.router, grades.router, risk.router,
          notifications.router, dashboard.router):
    app.include_router(r)


@app.get("/health", tags=["Monitoring"])
def health():
    """Cloud Run / Uptime check uchun: bazaga ulanishni ham tekshiradi."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
