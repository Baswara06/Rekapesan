"""Login akun demo. Pemilik: Raihan."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.errors import ApiError
from app.core.security import buat_token, cocok_akun

router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
def login(body: LoginIn) -> dict[str, str]:
    if not cocok_akun(body.username, body.password):
        raise ApiError(401, "tidak_terautentikasi", "Nama pengguna atau kata sandi salah.")
    return {"token": buat_token(body.username)}
