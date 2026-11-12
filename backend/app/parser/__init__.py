"""Modul parser dan anonimisasi. Pemilik: Satria."""

from datetime import date
from typing import IO

from app.schemas import Message


def parse_export(file_or_text: IO[bytes] | bytes | str, batch_date: date) -> list[Message]:
    """Pecah ekspor WhatsApp (.txt/.zip atau teks tempel) menjadi pesan, sudah disaring dan diberi sidik."""
    raise NotImplementedError


def anonymize(text: str) -> str:
    """Samarkan nomor telepon dan pola identitas lain sebelum teks keluar dari modul."""
    raise NotImplementedError
