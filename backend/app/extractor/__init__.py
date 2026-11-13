"""Modul ekstraktor LLM dan pembaca bukti bayar. Pemilik: Pangeran."""

from app.extractor.ekstrak import extract_orders
from app.schemas import ProofSuggestion

__all__ = ["extract_orders", "read_payment_proof"]


async def read_payment_proof(image_bytes: bytes) -> ProofSuggestion:
    """Baca nama pengirim dan nominal dari tangkapan layar transfer. Hanya saran."""
    raise NotImplementedError
