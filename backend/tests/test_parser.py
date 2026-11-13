"""Uji parser ekspor WhatsApp. Potongan di sini buatan sendiri mengikuti format ekspor Android,
iPhone, dan salinan WhatsApp Web berbahasa Indonesia (nama dan isi samaran)."""

import io
import zipfile
from datetime import date, datetime
from pathlib import Path

import pytest

from app.parser import FormatTidakDikenal, parse_export, pecah_pesan, saring_baru

CONTOH = Path(__file__).resolve().parents[2] / "sample" / "ekspor-contoh.txt"

ANDROID = """12/11/26 08.02 - Pesan dan panggilan dienkripsi secara end-to-end.
12/11/26 08.02 - Dewi membuat grup "PO: Katering Kantor"
12/11/26 09.15 - Bu Rina: ayam bakar 2 ya, kirim ke Blok C no 4
12/11/26 09.17 - Pak Anton: aybak 1 sama es teh 1
untuk jam 12 ya
12/11/26 10.05 - Pak Anton: <Media tidak disertakan>
12/11/26 10.06 - Pak Anton: IMG-20261112-WA0001.jpg (file terlampir)
ini bukti transfernya
12/11/26 10.07 - Bu Rina: Pesan ini telah dihapus
12/11/26 10.08 - +62 812-3456-7890: lodeh 1 <Pesan ini diedit>
"""

IPHONE = (
    "﻿[12/11/26 08.02.11] PO Katering: ‎Pesan dan panggilan dienkripsi secara end-to-end.\n"
    "[12/11/26 09.15.40] Bu Rina: ayam bakar 2 ya, kirim ke Blok C no 4\n"
    "[12/11/26 09.17.02] Pak Anton: aybak 1 sama es teh 1\n"
    "untuk jam 12 ya\n"
    "‎[12/11/26 10.05.33] Pak Anton: ‎gambar tidak disertakan\n"
    "[12/11/2026, 10:20:05] Bu Rina: eh ganti jadi ayam bakar 3 ya\n"
)


def test_android_pesan_sistem_dan_media_dibuang():
    pesan = pecah_pesan(ANDROID)
    assert [(p.pengirim, p.isi) for p in pesan] == [
        ("Bu Rina", "ayam bakar 2 ya, kirim ke Blok C no 4"),
        ("Pak Anton", "aybak 1 sama es teh 1\nuntuk jam 12 ya"),
        ("Pak Anton", "ini bukti transfernya"),
        ("+62 812-3456-7890", "lodeh 1"),
    ]
    assert pesan[0].waktu == datetime(2026, 11, 12, 9, 15)


def test_iphone_dengan_detik_tahun_4_digit_dan_karakter_tak_terlihat():
    pesan = pecah_pesan(IPHONE)
    assert [(p.pengirim, p.isi) for p in pesan] == [
        ("Bu Rina", "ayam bakar 2 ya, kirim ke Blok C no 4"),
        ("Pak Anton", "aybak 1 sama es teh 1\nuntuk jam 12 ya"),
        ("Bu Rina", "eh ganti jadi ayam bakar 3 ya"),
    ]
    assert pesan[0].waktu == datetime(2026, 11, 12, 9, 15, 40)
    assert pesan[2].waktu == datetime(2026, 11, 12, 10, 20, 5)


def test_sidik_sama_antara_android_dan_iphone():
    a = {p.sidik for p in pecah_pesan(ANDROID)}
    i = pecah_pesan(IPHONE)
    assert i[0].sidik in a and i[1].sidik in a


def test_salinan_whatsapp_web_dan_jam_titik_dua():
    teks = "[09.15, 12/11/2026] Bu Rina: ayam bakar 2\n[9:17 PM, 12/11/2026] Pak Anton: es teh 1"
    pesan = pecah_pesan(teks)
    assert [p.waktu for p in pesan] == [datetime(2026, 11, 12, 9, 15), datetime(2026, 11, 12, 21, 17)]


def test_pesan_kembar_di_menit_yang_sama_punya_sidik_berbeda():
    teks = "12/11/26 09.15 - Bu Rina: ayam bakar 1\n12/11/26 09.15 - Bu Rina: ayam bakar 1\n"
    a, b = pecah_pesan(teks)
    assert a.sidik != b.sidik
    assert [p.sidik for p in pecah_pesan(teks)] == [a.sidik, b.sidik]  # stabil saat diurai ulang


def test_saringan_tanggal_batch():
    teks = "10/11/26 09.00 - Bu Rina: PO lama\n12/11/26 09.15 - Bu Rina: ayam bakar 2\n"
    assert [p.isi for p in parse_export(teks, date(2026, 11, 12))] == ["ayam bakar 2"]
    assert len(parse_export(teks, None)) == 2


def test_saring_baru_membuang_yang_sudah_ada():
    pesan = pecah_pesan(ANDROID)
    assert saring_baru(pesan, {p.sidik for p in pesan}) == []
    assert saring_baru(pesan, {pesan[0].sidik}) == pesan[1:]


def test_bytes_txt_dan_zip_sama_dengan_teks():
    dari_teks = parse_export(ANDROID, None)
    assert parse_export(ANDROID.encode("utf-8"), None) == dari_teks
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("catatan.txt", "bukan chat")
        z.writestr("Chat WhatsApp dengan PO Katering.txt", ANDROID)
    assert parse_export(buf.getvalue(), None) == dari_teks
    assert parse_export(io.BytesIO(buf.getvalue()), None) == dari_teks


def test_format_tidak_dikenal():
    with pytest.raises(FormatTidakDikenal):
        parse_export("halo ini bukan ekspor", None)
    with pytest.raises(FormatTidakDikenal):
        parse_export("", None)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("foto.jpg", b"x")
    with pytest.raises(FormatTidakDikenal):
        parse_export(buf.getvalue(), None)


def test_berkas_contoh_di_repo():
    pesan = parse_export(CONTOH.read_bytes(), date(2026, 11, 12))
    assert len(pesan) == 9
    assert pesan[2].isi == "aybak 1 sama es teh 1\nuntuk jam 12 ya"
    assert {p.pengirim for p in pesan} == {"Dewi", "Bu Rina", "Pak Anton", "Mbak Sari", "Mas Budi", "Mas Joko"}


# Bentuk baris di bawah ini diambil dari ekspor iPhone asli berbahasa Inggris (13 Nov 2026).
# Nama dan isi diganti samaran; yang dipertahankan hanya strukturnya.
IPHONE_INGGRIS = (
    "[12/11/26, 08.02.11] Bu Rina: \u200eMessages and calls are end-to-end encrypted.\n"
    "[12/11/26, 09.15.40] Bu Rina: ayam bakar 2 ya \u200eimage omitted\n"
    "\u200e[12/11/26, 09.16.02] Bu Rina: \u200eimage omitted\n"
    "[12/11/26, 09.17.30] Pak Anton: lodeh 1 aja \u200e<This message was edited>\n"
    "[12/11/26, 09.18.00] Pak Anton: \u200eYou deleted this message.\n"
    "[12/11/26, 09.19.00] Pak Anton: \u200eMissed voice call. \u200eTap to call back\n"
    "[12/11/26, 09.20.00] Bu Rina: \u200eYour security code with Pak Anton changed.\n"
    "[12/11/26, 09.21.00] Bu Rina: es teh 1\n"
    "kirim jam 12 \u200evideo omitted\n"
)


def test_iphone_inggris_media_berketerangan_dan_pesan_sistem():
    pesan = pecah_pesan(IPHONE_INGGRIS)
    assert [(p.pengirim, p.isi) for p in pesan] == [
        ("Bu Rina", "ayam bakar 2 ya"),  # keterangan gambar dipertahankan, penandanya dibuang
        ("Pak Anton", "lodeh 1 aja"),
        ("Bu Rina", "es teh 1\nkirim jam 12"),
    ]
    assert not any("\u200e" in p.isi for p in pesan)


def test_karakter_tak_terlihat_di_tengah_isi_dibuang_tanpa_memotong_teks():
    teks = "12/11/26 09.15 - Bu Rina: ayam \u200ebakar 2, tolong jangan image omitted ya\n"
    assert pecah_pesan(teks)[0].isi == "ayam bakar 2, tolong jangan image omitted ya"
