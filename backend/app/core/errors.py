"""Kesalahan API yang seragam sesuai `docs/api-contract.md`. Pemilik: Raihan.

Bentuk: {"error": {"kode": "...", "pesan": "..."}}
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

KODE_PER_STATUS = {
    401: "tidak_terautentikasi",
    404: "tidak_ditemukan",
    422: "validasi_gagal",
}


class ApiError(Exception):
    def __init__(self, status: int, kode: str, pesan: str) -> None:
        super().__init__(pesan)
        self.status = status
        self.kode = kode
        self.pesan = pesan


def galat(status: int, kode: str, pesan: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"kode": kode, "pesan": pesan}})


def tidak_ditemukan(apa: str) -> ApiError:
    return ApiError(404, "tidak_ditemukan", f"{apa} tidak ditemukan.")


def validasi(pesan: str, status: int = 422) -> ApiError:
    return ApiError(status, "validasi_gagal", pesan)


def _ringkas_validasi(exc: RequestValidationError) -> str:
    err = exc.errors()[0]
    lokasi = ".".join(str(x) for x in err["loc"] if x not in ("body", "query", "path"))
    return f"Isian tidak valid ({lokasi}): {err['msg']}" if lokasi else f"Isian tidak valid: {err['msg']}"


def pasang_penanganan_galat(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_req: Request, exc: ApiError) -> JSONResponse:
        return galat(exc.status, exc.kode, exc.pesan)

    @app.exception_handler(RequestValidationError)
    async def _validasi(_req: Request, exc: RequestValidationError) -> JSONResponse:
        return galat(422, "validasi_gagal", _ringkas_validasi(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        kode = KODE_PER_STATUS.get(exc.status_code, "validasi_gagal")
        return galat(exc.status_code, kode, str(exc.detail))
