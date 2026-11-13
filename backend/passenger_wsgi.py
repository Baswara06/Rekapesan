"""Titik masuk aplikasi di cPanel (Setup Python App / Passenger). Pemilik: Satria.

Passenger berbicara WSGI, sedangkan FastAPI berbicara ASGI, jadi aplikasi dibungkus `a2wsgi`.
Tidak dipakai saat menjalankan di localhost (di sana tetap `uvicorn app.main:app`).

- Folder kerja dipindah ke folder berkas ini, karena `.env` dan `DATABASE_URL` relatif dibaca dari sana.
- `init_db()` dipanggil di sini, karena a2wsgi tidak menjalankan lifespan FastAPI (diuji: tanpa ini
  tabel tidak pernah terbuat).
"""

import os
import sys

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)
if DIR not in sys.path:
    sys.path.insert(0, DIR)

from a2wsgi import ASGIMiddleware  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
application = ASGIMiddleware(app)
