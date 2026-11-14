from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import agen, auth, batches, harian, health, impor, menu_baru, orders, pembayaran, products, recap
from app.core.config import get_settings
from app.core.errors import pasang_penanganan_galat
from app.core.security import require_login
from app.db import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()  # buat tabel yang belum ada
    yield


app = FastAPI(title="Rekapesan", version="0.1.0", lifespan=lifespan)
pasang_penanganan_galat(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Terbuka: cek kesehatan dan login.
app.include_router(health.router)
app.include_router(auth.router)

# Semua yang lain wajib login (header Authorization: Bearer <token>).
terlindungi = [Depends(require_login)]
for modul in (impor, harian, menu_baru, products, batches, orders, recap, pembayaran, agen):
    app.include_router(modul.router, dependencies=terlindungi)
