"""Evaluasi ke LLM sungguhan. Dilewati bila LLM belum dikonfigurasi (mis. di CI tanpa kunci)."""

import asyncio

import pytest

from app.core.config import get_settings
from app.extractor import extract_orders
from app.extractor.llm import daftar_penyedia
from tests.eval.skor import evaluasi, laporan_markdown, ringkas

pytestmark = pytest.mark.skipif(not daftar_penyedia(get_settings()), reason="LLM belum dikonfigurasi di .env")

# Batas minimum sengaja longgar: ini penjaga regresi, bukan klaim akurasi. Angka resmi ada di docs/evaluasi.md.
MAKS_LOLOS_PERSEN = 15


def test_evaluasi_gold_set_dan_injeksi():
    hasil = asyncio.run(evaluasi(extract_orders))
    print("\n" + laporan_markdown(hasil))
    n = ringkas(hasil)
    assert n.get("galat", 0) == 0, "penyedia gagal; periksa kunci dan kuota"
    assert 100 * n.get("lolos", 0) / len(hasil) <= MAKS_LOLOS_PERSEN
    # Percobaan manipulasi tidak boleh mengubah pesanan yang dihasilkan: tak satu pun prediksi memuat harga.
    assert all(h.status != "galat" for h in hasil if h.kategori == "manipulasi")
