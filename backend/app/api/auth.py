"""Login, register, dan profil akun penjual. Pemilik: Raihan.

Akun demo tetap dari `.env` (nama toko dari `DEMO_NAMA_TOKO`). Akun baru disimpan di tabel `users`
(kata sandi di-hash). Setiap akun hanya melihat katalog dan batch miliknya sendiri.
"""

import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.kepemilikan import nama_toko_akun
from app.core import security
from app.core.config import KUNCI_MINIMAL
from app.core.errors import ApiError, validasi
from app.core.security import buat_token, cek_password, cocok_akun, hash_password, kunci_sah, require_login
from app.db import User, get_db

router = APIRouter(prefix="/api")

POLA_USERNAME = re.compile(r"^[a-z0-9_.]{3,32}$")
SANDI_MINIMAL = 8
NAMA_TOKO_MINIMAL = 2
NAMA_TOKO_MAKSIMAL = 60


class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(LoginIn):
    # Opsional di API supaya klien lama tetap bisa daftar; layar Daftar mewajibkannya.
    nama_toko: str | None = None


class AkunIn(BaseModel):
    nama_toko: str


def _rapikan_nama_toko(nama: str | None) -> str | None:
    """Rapikan spasi. Kosong menjadi `None`. Panjang di luar batas ditolak 422."""
    nama = " ".join((nama or "").split())
    if not nama:
        return None
    if not NAMA_TOKO_MINIMAL <= len(nama) <= NAMA_TOKO_MAKSIMAL:
        raise validasi(f"Nama toko {NAMA_TOKO_MINIMAL}-{NAMA_TOKO_MAKSIMAL} karakter.")
    return nama


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
def register(body: RegisterIn, db: Session = Depends(get_db)) -> dict[str, str]:
    _cek_kunci()
    username = body.username.strip().lower()
    if not POLA_USERNAME.fullmatch(username):
        raise validasi("Nama pengguna 3-32 karakter: huruf kecil, angka, titik, atau garis bawah.")
    if len(body.password) < SANDI_MINIMAL:
        raise validasi(f"Kata sandi minimal {SANDI_MINIMAL} karakter.")
    nama_toko = _rapikan_nama_toko(body.nama_toko)
    sudah_ada = ApiError(409, "username_dipakai", "Nama pengguna sudah dipakai. Pilih nama lain.")
    dipakai = username == security.get_settings().demo_username.lower()
    if dipakai or db.scalar(select(User).where(User.username == username)):

        raise sudah_ada
    db.add(User(username=username, password_hash=hash_password(body.password), nama_toko=nama_toko))
    try:
        db.commit()
    except IntegrityError:  # dua register bersamaan dengan nama yang sama
        db.rollback()
        raise sudah_ada from None
    return {"token": buat_token(username)}


@router.get("/auth/me")
def akun_saya(db: Session = Depends(get_db), username: str = Depends(require_login)) -> dict[str, str | None]:
    return {"username": username, "nama_toko": nama_toko_akun(db, username)}


@router.patch("/auth/me")
def ubah_akun(body: AkunIn, db: Session = Depends(get_db), username: str = Depends(require_login)) -> dict[str, str | None]:
    if username == security.get_settings().demo_username:
        raise validasi("Nama toko akun demo diatur lewat DEMO_NAMA_TOKO di .env.", status=409)
    nama_toko = _rapikan_nama_toko(body.nama_toko)
    if nama_toko is None:
        raise validasi("Nama toko wajib diisi.")
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise ApiError(401, "tidak_terautentikasi", "Akun tidak ditemukan. Silakan masuk lagi.")
    user.nama_toko = nama_toko
    db.commit()
    return {"username": username, "nama_toko": nama_toko}
