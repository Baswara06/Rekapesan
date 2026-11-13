"""Autentikasi sederhana: satu akun demo, token bertanda tangan HMAC. Pemilik: Raihan.

Token = base64url(JSON {sub, exp}) + "." + base64url(HMAC-SHA256). Tanpa pustaka tambahan.
Kunci dari `APP_SECRET_KEY`, akun dari `DEMO_USERNAME` dan `DEMO_PASSWORD` di `.env`.
"""

import base64
import hashlib
import hmac
import json
import time

from fastapi import Request

from app.core.config import KUNCI_BAWAAN, KUNCI_MINIMAL, get_settings
from app.core.errors import ApiError

MASA_BERLAKU_DETIK = 12 * 3600


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(teks: str) -> bytes:
    return base64.urlsafe_b64decode(teks + "=" * (-len(teks) % 4))


def kunci_sah() -> bool:
    """Kunci penanda tangan wajib diisi sendiri: bukan kosong, bukan nilai bawaan yang publik, minimal 16 karakter."""
    kunci = get_settings().app_secret_key
    return bool(kunci) and kunci != KUNCI_BAWAAN and len(kunci) >= KUNCI_MINIMAL


def password_demo_ada() -> bool:
    return bool(get_settings().demo_password)


def _tanda_tangan(isi: str) -> str:
    kunci = get_settings().app_secret_key.encode()
    return _b64(hmac.new(kunci, isi.encode(), hashlib.sha256).digest())


def buat_token(username: str, sekarang: float | None = None) -> str:
    if not kunci_sah():
        raise ValueError("APP_SECRET_KEY belum diatur dengan benar.")
    isi = _b64(json.dumps({"sub": username, "exp": int((sekarang or time.time()) + MASA_BERLAKU_DETIK)}).encode())
    return f"{isi}.{_tanda_tangan(isi)}"


def periksa_token(token: str, sekarang: float | None = None) -> str | None:
    """Kembalikan username bila token sah dan belum kedaluwarsa, selain itu None."""
    if not kunci_sah():
        return None  # kunci lemah berarti siapa pun bisa menandatangani token sendiri
    try:
        isi, tanda = token.split(".", 1)
        if not hmac.compare_digest(tanda, _tanda_tangan(isi)):
            return None
        data = json.loads(_unb64(isi))
        if data["exp"] < (sekarang or time.time()):
            return None
        return str(data["sub"])
    except (ValueError, KeyError, TypeError):
        return None


def cocok_akun(username: str, password: str) -> bool:
    s = get_settings()
    if not kunci_sah() or not s.demo_password:
        return False  # akun demo belum diatur: tolak semua, jangan buka akses tanpa kata sandi
    ok_user = hmac.compare_digest(username.encode(), s.demo_username.encode())
    ok_pass = hmac.compare_digest(password.encode(), s.demo_password.encode())
    return ok_user and ok_pass


def require_login(request: Request) -> str:
    """Dependency: wajib header `Authorization: Bearer <token>`."""
    header = request.headers.get("authorization", "")
    skema, _, token = header.partition(" ")
    user = periksa_token(token.strip()) if skema.lower() == "bearer" and token else None
    if user is None:
        raise ApiError(401, "tidak_terautentikasi", "Masuk dulu untuk memakai fitur ini.")
    return user
