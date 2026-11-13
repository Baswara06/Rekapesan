"""Anonimisasi teks sebelum keluar ke LLM. Pemilik: Satria.

Deterministik dan tanpa keadaan. Yang disamarkan: nomor telepon, alamat surel, dan deret
angka panjang (nomor rekening, NIK). Angka pendek seperti jumlah, harga, dan jam dibiarkan.
"""

import re

GANTI_NOMOR = "[nomor]"
GANTI_EMAIL = "[email]"
GANTI_ANGKA = "[angka]"

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# +62 812-3456-7890, 62 812 3456 7890, 0812.3456.7890, (0812) 34567890, @6281234567890
_TELEPON = re.compile(r"(?<![\d\w])@?\(?(?:\+?62|0)\)?[\s.\-]?8(?:[\s.\-()]{0,2}\d){7,11}(?!\d)")
# Nomor asing dengan awalan +: +1 415 555 0100
_TELEPON_INTL = re.compile(r"(?<![\d\w])\+\d(?:[\s.\-()]{0,2}\d){7,14}(?!\d)")
# Deret 10 digit atau lebih, boleh dipisah spasi/strip tunggal: rekening, NIK, kartu.
_ANGKA_PANJANG = re.compile(r"(?<![\d\w])\d(?:[ \-]?\d){9,}(?!\d)")


def anonymize(text: str) -> str:
    """Samarkan nomor telepon dan pola identitas lain sebelum teks keluar dari modul."""
    if not text:
        return text
    hasil = _EMAIL.sub(GANTI_EMAIL, text)
    hasil = _TELEPON.sub(GANTI_NOMOR, hasil)
    hasil = _TELEPON_INTL.sub(GANTI_NOMOR, hasil)
    return _ANGKA_PANJANG.sub(GANTI_ANGKA, hasil)
