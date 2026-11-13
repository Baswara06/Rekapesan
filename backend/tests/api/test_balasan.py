from app.api.balasan import rupiah, susun_balasan


def test_format_rupiah_titik_ribuan():
    assert rupiah(0) == "Rp0"
    assert rupiah(36000) == "Rp36.000"
    assert rupiah(1250000) == "Rp1.250.000"


def test_balasan_lengkap():
    teks = susun_balasan(
        "Bu Rina",
        [
            {"nama": "Ayam Bakar", "qty": 3, "harga_satuan": 18000, "catatan_item": "pedas", "dikenal": True},
            {"nama": "Es Teh", "qty": 1, "harga_satuan": 5000, "catatan_item": None, "dikenal": True},
        ],
        59000,
        "12:00",
        "Blok C no 4",
        "jangan pakai sambal",
    )
    assert teks.splitlines() == [
        "Halo Bu Rina, pesanan kamu sudah kami catat ya:",
        "- 3 x Ayam Bakar = Rp54.000 (pedas)",
        "- 1 x Es Teh = Rp5.000",
        "Total: Rp59.000",
        "Dikirim pukul 12.00 ke Blok C no 4.",
        "Catatan: jangan pakai sambal",
        "Terima kasih!",
    ]


def test_balasan_tanpa_jam_alamat_dan_item_bermasalah():
    teks = susun_balasan(
        "Pak Anton",
        [
            {"nama": "rendang", "qty": 2, "harga_satuan": None, "catatan_item": None, "dikenal": False},
            {"nama": "lodeh", "qty": None, "harga_satuan": 15000, "catatan_item": None, "dikenal": True},
        ],
        0,
        None,
        None,
        None,
    )
    assert "- 2 x rendang (harga belum ada)" in teks
    assert "- lodeh (jumlah belum jelas)" in teks
    assert "Dikirim" not in teks and "Catatan" not in teks
    assert teks.endswith("Terima kasih!")
