"""Login dan register akun penjual. Pemilik: Raihan.

Akun demo tetap dari `.env`. Akun baru disimpan di tabel `users` (kata sandi di-hash).
Setiap akun hanya melihat katalog dan batch miliknya sendiri.
"""

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import KUNCI_MINIMAL
from app.core.errors import ApiError, validasi
from app.core.security import buat_token, cek_password, cocok_akun, hash_password, kunci_sah
from app.db import User, get_db

router = APIRouter(prefix="/api")

POLA_USERNAME = re.compile(r"^[a-z0-9_.]{3,32}$")
SANDI_MINIMAL = 8


class LoginIn(BaseModel):
    username: str
    password: str


def _cek_kunci() -> None:
    if not kunci_sah():
        raise ApiError(
            401,
            "tidak_terautentikasi",
            f"Login dimatikan: APP_SECRET_KEY di .env kosong, masih nilai bawaan, atau kurang dari {KUNCI_MINIMAL} karakter.",
        )


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict[str, str]:
    _cek_kunci()
    s = security.get_settings()
    if body.username == s.demo_username:
        if not s.demo_password:
            raise ApiError(401, "tidak_terautentikasi", "Login dimatikan: DEMO_PASSWORD di .env belum diisi.")
        if cocok_akun(body.username, body.password):
            return {"token": buat_token(body.username)}
    else:
        user = db.scalar(select(User).where(User.username == body.username.strip().lower()))
        if user is not None and cek_password(body.password, user.password_hash):
            return {"token": buat_token(user.username)}
    raise ApiError(401, "tidak_terautentikasi", "Nama pengguna atau kata sandi salah.")


@router.post("/auth/register", status_code=201)
def register(body: LoginIn, db: Session = Depends(get_db)) -> dict[str, str]:
    _cek_kunci()
    username = body.username.strip().lower()
    if not POLA_USERNAME.fullmatch(username):
        raise validasi("Nama pengguna 3-32 karakter: huruf kecil, angka, titik, atau garis bawah.")
    if len(body.password) < SANDI_MINIMAL:
        raise validasi(f"Kata sandi minimal {SANDI_MINIMAL} karakter.")
    sudah_ada = ApiError(409, "username_dipakai", "Nama pengguna sudah dipakai. Pilih nama lain.")
    dipakai = username == security.get_settings().demo_username.lower()
    if dipakai or db.scalar(select(User).where(User.username == username)):

        raise sudah_ada
    db.add(User(username=username, password_hash=hash_password(body.password)))
    try:
        db.commit()
    except IntegrityError:  # dua register bersamaan dengan nama yang sama
        db.rollback()
        raise sudah_ada from None
    return {"token": buat_token(username)}
