"""Pemecah ekspor chat WhatsApp (Android, iPhone, salinan WhatsApp Web). Pemilik: Satria.

Seluruh modul ini deterministik: tidak ada LLM. Keluarannya daftar `Message` yang sudah
bersih dari pesan sistem dan penanda media, sudah disaring tanggal, dan sudah diberi sidik.
"""

import hashlib
import io
import re
import zipfile
from datetime import date, datetime
from typing import IO

from app.schemas import Message

MAKS_UKURAN_BYTE = 20 * 1024 * 1024


class FormatTidakDikenal(ValueError):
    """Berkas atau teks bukan ekspor WhatsApp yang dikenali (kode API: format_file_tidak_dikenal)."""


_TAK_TERLIHAT = "‎‏‪‫‬‭‮⁦⁧⁨⁩﻿"
_PENANDA_SISTEM_IOS = "‎"

_TGL = r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})"
_JAM = r"(\d{1,2})[.:](\d{2})(?:[.:](\d{2}))?(?:\s?([AaPp])\.?[Mm]\.?)?"

# Android:  12/11/26 08.02 - Nama: isi      |  12/11/2026, 08:02 - Nama: isi
_ANDROID = re.compile(rf"^{_TGL},?\s+{_JAM}\s+-\s(.*)$")
# iPhone:   [12/11/26 08.02.15] Nama: isi   |  [12/11/2026, 08:02:15] Nama: isi
_IPHONE = re.compile(rf"^\[{_TGL},?\s+{_JAM}\]\s?(.*)$")
# Salin dari WhatsApp Web/Desktop: [08.02, 12/11/2026] Nama: isi
_WEB = re.compile(rf"^\[{_JAM},\s+{_TGL}\]\s?(.*)$")

_PENGIRIM = re.compile(r"^([^:\n]{1,80}?):(?:\s(.*))?$", re.DOTALL)
# Pesan sistem Android yang kebetulan memuat titik dua (mis. nama grup "PO: Jumat").
_KATA_SISTEM = re.compile(
    r"\s(membuat grup|menambahkan|mengeluarkan|mengubah (subjek|ikon|deskripsi|setelan)|telah keluar|bergabung "
    r"(menggunakan|dari)|created group|added|changed (the|this) (subject|group))",
    re.I,
)

_MEDIA = [
    re.compile(r"^<[^<>]*(tidak disertakan|omitted|lampiran|attached)[^<>]*>$", re.I),
    re.compile(
        r"^(gambar|foto|video|stiker|audio|dokumen|gif|kartu kontak|lokasi|image|sticker|document|contact card)"
        r"\s+(tidak disertakan|omitted)$",
        re.I,
    ),
    re.compile(r"^.+\((file terlampir|file attached)\)$", re.I),
]
_DIHAPUS = {
    "pesan ini telah dihapus",
    "pesan ini dihapus",
    "anda menghapus pesan ini",
    "this message was deleted",
    "you deleted this message",
    "menunggu pesan ini",
    "waiting for this message",
}
_DIEDIT = re.compile(r"\s*<(pesan ini diedit|this message was edited)>\s*$", re.I)


def baca_teks(file_or_text: IO[bytes] | bytes | str) -> str:
    """Ubah masukan apa pun (teks tempel, bytes .txt, bytes .zip, berkas terbuka) menjadi teks."""
    if isinstance(file_or_text, str):
        return file_or_text
    data = file_or_text if isinstance(file_or_text, bytes) else file_or_text.read(MAKS_UKURAN_BYTE + 1)
    if len(data) > MAKS_UKURAN_BYTE:
        raise FormatTidakDikenal("Berkas terlalu besar (maksimal 20 MB).")
    if data[:4] == b"PK\x03\x04":
        data = _txt_dari_zip(data)
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("utf-16", errors="replace") if data[:2] in (b"\xff\xfe", b"\xfe\xff") else data.decode(
            "latin-1"
        )


def _txt_dari_zip(data: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as arsip:
            kandidat = [i for i in arsip.infolist() if i.filename.lower().endswith(".txt") and not i.is_dir()]
            if not kandidat:
                raise FormatTidakDikenal("Berkas .zip tidak berisi berkas .txt.")
            # Ekspor iPhone bernama `_chat.txt`, Android `Chat WhatsApp dengan ...txt`.
            kandidat.sort(key=lambda i: ("chat" not in i.filename.lower(), -i.file_size))
            info = kandidat[0]
            if info.file_size > MAKS_UKURAN_BYTE:
                raise FormatTidakDikenal("Berkas chat di dalam .zip terlalu besar (maksimal 20 MB).")
            return arsip.read(info)
    except zipfile.BadZipFile as exc:
        raise FormatTidakDikenal("Berkas .zip rusak atau tidak bisa dibuka.") from exc


def _waktu(hari: str, bulan: str, tahun: str, jam: str, menit: str, detik: str | None, ampm: str | None):
    y = int(tahun)
    if y < 100:
        y += 2000
    h = int(jam)
    if ampm:
        h = h % 12 + (12 if ampm.lower() == "p" else 0)
    try:
        return datetime(y, int(bulan), int(hari), h, int(menit), int(detik or 0))
    except ValueError:
        return None


def _baca_kepala(baris: str) -> tuple[datetime, str] | None:
    """Kembalikan (waktu, sisa baris) bila baris adalah awal pesan, selain itu None."""
    bersih = baris.lstrip(_TAK_TERLIHAT).replace(" ", " ").replace("\xa0", " ")
    for pola, web in ((_ANDROID, False), (_IPHONE, False), (_WEB, True)):
        m = pola.match(bersih)
        if not m:
            continue
        g = m.groups()
        if web:
            jam, menit, detik, ampm, hari, bulan, tahun, sisa = g
        else:
            hari, bulan, tahun, jam, menit, detik, ampm, sisa = g
        waktu = _waktu(hari, bulan, tahun, jam, menit, detik, ampm)
        if waktu is not None:
            return waktu, sisa
    return None


_SEMUA_TAK_TERLIHAT = re.compile("[" + _TAK_TERLIHAT + "]")
_MEDIA_KURUNG = re.compile(r"<[^<>\n]*(tidak disertakan|omitted)[^<>\n]*>", re.I)


def _bersihkan_isi(isi: str) -> str:
    """Buang penanda media, penanda edit, dan karakter tak terlihat. Kosong berarti pesan dibuang."""
    baris_bersih = []
    for baris in isi.split("\n"):
        b = _DIEDIT.sub("", baris.strip(_TAK_TERLIHAT + " \t\r"))
        # iPhone menulis media berketerangan dalam satu baris: "keterangan <U+200E>image omitted".
        # Penanda di belakang U+200E dibuang, keterangannya dipertahankan.
        # Bisa ada lebih dari satu U+200E di satu baris, jadi potong dari penanda paling belakang.
        while True:
            depan, pemisah, ekor = b.rpartition(_PENANDA_SISTEM_IOS)
            if not pemisah:
                break
            if ekor.strip() and not _penanda_media(ekor):
                break
            b = depan.rstrip()
        # Android menulisnya dalam kurung sudut di baris yang sama: "keterangan <Media omitted>".
        b = _MEDIA_KURUNG.sub(" ", b)
        b = re.sub(r" {2,}", " ", _SEMUA_TAK_TERLIHAT.sub("", b)).strip()
        if _penanda_media(b):
            continue
        baris_bersih.append(b)
    hasil = "\n".join(baris_bersih).strip()
    return "" if hasil.lower().rstrip(".") in _DIHAPUS else hasil


def _penanda_media(teks: str) -> bool:
    teks = _SEMUA_TAK_TERLIHAT.sub("", teks).strip()
    return bool(teks) and any(p.match(teks) for p in _MEDIA)


def sidik_pesan(waktu: datetime, pengirim: str, isi: str, urutan: int) -> str:
    """sha256(waktu + pengirim + isi + urutan_dalam_menit_yang_sama).

    Waktu dibulatkan ke menit supaya ekspor Android (tanpa detik) dan iPhone (dengan detik)
    dari chat yang sama menghasilkan sidik yang sama. `urutan` membedakan pesan kembar
    (pengirim dan isi sama) di menit yang sama.
    """
    kunci = f"{waktu:%Y-%m-%dT%H:%M}|{pengirim}|{isi}|{urutan}"
    return hashlib.sha256(kunci.encode("utf-8")).hexdigest()


def pecah_pesan(teks: str) -> list[Message]:
    """Pecah teks ekspor menjadi pesan pengguna (tanpa saringan tanggal), lengkap dengan sidik."""
    mentah: list[tuple[datetime, str]] = []
    for baris in teks.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        kepala = _baca_kepala(baris)
        if kepala:
            mentah.append(kepala)
        elif mentah:
            waktu, isi = mentah[-1]
            mentah[-1] = (waktu, f"{isi}\n{baris}")

    if not mentah:
        raise FormatTidakDikenal(
            "Tidak ada pesan WhatsApp yang dikenali. Unggah berkas ekspor (.txt/.zip) atau tempel "
            "teks hasil ekspor chat."
        )

    pesan: list[Message] = []
    kembar: dict[tuple[str, str, str], int] = {}
    for waktu, sisa in mentah:
        m = _PENGIRIM.match(sisa)
        if not m:
            continue  # pesan sistem: tidak punya "Pengirim: "
        pengirim = m.group(1).strip(_TAK_TERLIHAT + " ")
        if _KATA_SISTEM.search(pengirim):
            continue
        isi_mentah = m.group(2) or ""
        if isi_mentah.startswith(_PENANDA_SISTEM_IOS):
            continue  # iPhone menandai pesan sistem dan media dengan U+200E di awal isi
        isi = _bersihkan_isi(isi_mentah)
        if not pengirim or not isi:
            continue
        kunci = (f"{waktu:%Y-%m-%dT%H:%M}", pengirim, isi)
        urutan = kembar.get(kunci, 0)
        kembar[kunci] = urutan + 1
        pesan.append(Message(waktu=waktu, pengirim=pengirim, isi=isi, sidik=sidik_pesan(waktu, pengirim, isi, urutan)))
    return pesan


def saring_tanggal(pesan: list[Message], batch_date: date | None) -> list[Message]:
    """Simpan pesan sejak `batch_date` (tanggal chat PO dibuka). None berarti tanpa saringan."""
    if batch_date is None:
        return pesan
    return [p for p in pesan if p.waktu.date() >= batch_date]


def saring_baru(pesan: list[Message], sidik_ada: set[str]) -> list[Message]:
    """Buang pesan yang sidiknya sudah ada di DB. Dasar impor ulang tanpa pesanan dobel."""
    return [p for p in pesan if p.sidik not in sidik_ada]


def parse_export(file_or_text: IO[bytes] | bytes | str, batch_date: date | None) -> list[Message]:
    """Pecah ekspor WhatsApp (.txt/.zip atau teks tempel) menjadi pesan, sudah disaring dan diberi sidik."""
    return saring_tanggal(pecah_pesan(baca_teks(file_or_text)), batch_date)
