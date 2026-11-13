import pytest

from app.parser import anonymize


@pytest.mark.parametrize(
    "teks",
    [
        "hubungi 081234567890 ya",
        "wa ke +62 812-3456-7890",
        "nomor 62 812 3456 7890",
        "0812.3456.7890",
        "0812 3456 789",
        "cc @6281234567890",
        "(0812) 3456-7890",
        "+1 415 555 0100",
    ],
)
def test_nomor_telepon_disamarkan(teks):
    hasil = anonymize(teks)
    assert "[nomor]" in hasil
    assert not any(c.isdigit() for c in hasil)


def test_pengirim_berupa_nomor():
    assert anonymize("+62 812-3456-7890") == "[nomor]"


def test_email_dan_rekening_disamarkan():
    assert anonymize("kirim ke rina.s@contoh.co.id") == "kirim ke [email]"
    assert anonymize("tf BCA 1234567890 a.n. Dewi") == "tf BCA [angka] a.n. Dewi"
    assert anonymize("NIK 3578 0101 0190 0001") == "NIK [angka]"


@pytest.mark.parametrize(
    "teks",
    [
        "ayam bakar 2 ya, kirim ke Blok C no 4",
        "lodeh 3, jam 11.30 ke lantai 2",
        "ayam bakar 500",
        "total 180000 ya, kirim 12/11/2026 jam 08.10",
        "",
    ],
)
def test_angka_pesanan_tidak_berubah(teks):
    assert anonymize(teks) == teks
