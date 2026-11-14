"""Titik masuk aplikasi di cPanel (Setup Python App / Passenger). Pemilik: Satria.

Passenger berbicara WSGI, sedangkan FastAPI berbicara ASGI, jadi aplikasi dibungkus `a2wsgi`.
Tidak dipakai saat menjalankan di localhost (di sana tetap `uvicorn app.main:app`).

- Folder kerja dipindah ke folder berkas ini, karena `.env` dan `DATABASE_URL` relatif dibaca dari sana.
- `init_db()` dipanggil di sini, karena a2wsgi tidak menjalankan lifespan FastAPI (diuji: tanpa ini
  tabel tidak pernah terbuat).
- Pembungkus a2wsgi dan `init_db()` dibuat saat request pertama, bukan saat berkas dimuat. Passenger
  memuat berkas ini lalu fork; a2wsgi menyalakan thread event loop di konstruktornya, dan thread tidak
  ikut ke proses hasil fork, sehingga setiap request menggantung (diuji dengan os.fork).
"""

import os
import sys
import threading

DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(DIR)
if DIR not in sys.path:
    sys.path.insert(0, DIR)

from a2wsgi import ASGIMiddleware  # noqa: E402

from app.db import init_db  # noqa: E402
from app.main import app  # noqa: E402

_kunci = threading.Lock()
_wsgi = None


def application(environ, start_response):
    global _wsgi
    if _wsgi is None:
        with _kunci:
            if _wsgi is None:
                init_db()
                _wsgi = ASGIMiddleware(app)
    return _wsgi(environ, start_response)
