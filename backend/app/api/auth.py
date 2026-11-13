"""Login akun demo. Pemilik: Raihan."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import KUNCI_MINIMAL
from app.core.errors import ApiError
from app.core.security import buat_token, cocok_akun, kunci_sah, password_demo_ada

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn) -> dict[str, str]:
    if not kunci_sah():
        raise ApiError(
            401,
            "tidak_terautentikasi",
            f"Login dimatikan: APP_SECRET_KEY di .env kosong, masih nilai bawaan, atau kurang dari {KUNCI_MINIMAL} karakter.",
        )
    if not password_demo_ada():
        raise ApiError(401, "tidak_terautentikasi", "Login dimatikan: DEMO_PASSWORD di .env belum diisi.")
    if not cocok_akun(body.username, body.password):
        raise ApiError(401, "tidak_terautentikasi", "Nama pengguna atau kata sandi salah.")
    return {"token": buat_token(body.username)}
