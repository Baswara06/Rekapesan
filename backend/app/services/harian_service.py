"""Buku pesanan harian: pratinjau chat, impor per hari, dan papan ringkasan. Pemilik: Satria.

Semua di sini dihitung KODE, bukan LLM:
- deteksi penjual dan menu + harga dari pesan yang memuat minimal dua harga,
- pemecahan chat menjadi satu batch per tanggal (memakai `import_batch` yang sudah ada),
- ringkasan papan pesanan dan saran "sudah bayar/sudah terima" berbasis kata kunci.
Saran tidak pernah mengubah status. Penjual yang menekan tombol konfirmasi.
"""

import re
from collections import Counter
from datetime import date
from typing import IO, Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    STATUS_BATAL,
    STATUS_DIBAYAR,
    STATUS_DIKIRIM,
    STATUS_DISETUJUI,
    STATUS_PERLU_CEK,
    Batch,
    MessageRow,
    Order,
    Payment,
    Product,
)
from app.parser import parse_export
from app.schemas import Message
from app.services.import_service import ImportResult, import_batch

MAKS_HARI = 14
HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
BULAN = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")

# Harga: "17rb", "17 ribu", "17k", "17.000", "Rp17.000", "Rp 17000". Angka polos < 1000 dianggap jumlah, bukan harga.
_HARGA = re.compile(
    r"(?P<rp>rp\.?\s*)?(?P<angka>\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?P<sat>rb|ribu|k)?(?![\w.,]*\d)",
    re.IGNORECASE,
)
_PEMISAH_SEGMEN = re.compile(r"[\n,;]+")
_PEMISAH_KALIMAT = re.compile(r"[.!?:]\s+|[:=@]")
_AWALAN_DAFTAR = re.compile(r"^[\s\-–•*>#]*(\d+[.)]\s*)?")

_SUDAH_BAYAR = re.compile(
    r"\b(udah|sudah|dah|udh|sdh)\s+(di\s*)?(tf|trf|transfer|bayar|lunas)\b|\bbukti\s+(tf|trf|transfer|bayar)\b",
    re.IGNORECASE,
)
_SUDAH_TERIMA = re.compile(
    r"\b(udah|sudah|dah|udh|sdh)\s+(sampai|sampe|nyampe|nyampai|diterima|terima)\b",
    re.IGNORECASE,
)


def nama_hari(tanggal: date) -> str:
    return f"{HARI[tanggal.weekday()]}, {tanggal.day} {BULAN[tanggal.month - 1]}"


def baca_harga(teks: str) -> list[tuple[int, int, int]]:
    """Daftar (awal, akhir, harga rupiah) untuk setiap harga di teks."""
    hasil = []
    for m in _HARGA.finditer(teks):
        angka = int(re.sub(r"[.,]", "", m["angka"]))
        if m["sat"]:
            nilai = angka * 1000
        elif m["rp"] or re.search(r"[.,]", m["angka"]) or angka >= 1000:
            nilai = angka
        else:
            continue  # angka kecil tanpa satuan: jumlah porsi atau jam, bukan harga
        if 500 <= nilai <= 10_000_000:
            hasil.append((m.start(), m.end(), nilai))
    return hasil


def _nama_menu(sebelum_harga: str) -> str | None:
    potongan = [p for p in _PEMISAH_KALIMAT.split(sebelum_harga) if p.strip()]
    if not potongan:
        return None
    nama = potongan[-1]
    nama = _AWALAN_DAFTAR.sub("", nama).strip(" -–:=@*()[]").strip()
    nama = re.sub(r"\s+", " ", nama)
    nama = re.sub(r"\b(harga(nya)?|cuma|hanya)\s*$", "", nama, flags=re.IGNORECASE).strip()
    if not (2 <= len(nama) <= 60) or not re.search(r"[A-Za-z]", nama):
        return None
    return nama


def menu_dari_pesan(isi: str) -> list[tuple[str, int]]:
    """Menu + harga dari satu pesan. Pesan dianggap daftar menu hanya bila memuat minimal dua harga,
    supaya pesan seperti "ubah harga ayam jadi 1000" tidak terbaca sebagai menu."""
    if len(baca_harga(isi)) < 2:
        return []
    menu = []
    for segmen in _PEMISAH_SEGMEN.split(isi):
        harga = baca_harga(segmen)
        if len(harga) != 1:
            continue
        nama = _nama_menu(segmen[: harga[0][0]])
        if nama:
            menu.append((nama, harga[0][2]))
    return menu


# Kata yang tidak pernah jadi nama menu di pesan pembeli. Angka setelah kata-kata alamat/waktu bukan jumlah porsi.
_KATA_PENGISI = {
    "kak", "ka", "kakak", "mbak", "mba", "mas", "bu", "pak", "bang", "om", "ya", "yaa", "yah", "dong", "deh", "aja", "sih",
    "mau", "pesan", "pesen", "order", "aku", "saya", "gue", "gua", "tolong", "jadi", "jadinya", "ganti", "tambah", "sama",
    "dan", "terus", "lagi", "juga", "eh", "maaf", "nih", "ini", "itu", "yang", "ada", "ga", "gak", "nggak", "kah", "buat",
    "untuk", "x", "porsi", "pcs", "bungkus", "bks", "biji", "buah", "nya", "total", "semua",
}
_KATA_ALAMAT = {
    "jam", "pukul", "blok", "kamar", "lt", "lantai", "jl", "jln", "jalan", "no", "nomor", "rt", "rw", "gang", "gg", "kos",
    "kost", "kantor", "kirim", "alamat", "perum", "tgl", "tanggal", "hari", "menit", "rb", "ribu", "k", "rp", "kelas",
}
_ANGKA_JUMLAH = re.compile(r"(?<![\d.:/,])\b(\d{1,3})\b(?![.:/,]?\d)")


def _ringkas(teks: str) -> str:
    return re.sub(r"[^a-z]", "", teks.lower())


def _kata_bersih(kata: str) -> str:
    kata = kata.lower()
    return kata[:-3] if kata.endswith("nya") and len(kata) > 5 else kata


def calon_menu_pembeli(isi: str) -> list[str]:
    """Tebakan nama menu dari pesan pembeli: kata-kata tepat sebelum (atau sesudah) sebuah jumlah, mis. "geprek 2"."""
    calon = []
    for segmen in re.split(r"[\n,;+&]|\bsama\b|\bdan\b", isi, flags=re.IGNORECASE):
        batas = 0  # kata untuk sebuah jumlah hanya diambil sejak jumlah sebelumnya ("bawang putih 1 ketumbar 1")
        for m in _ANGKA_JUMLAH.finditer(segmen):
            sebelum = [_kata_bersih(k) for k in re.findall(r"[A-Za-z]+", segmen[batas : m.start()])]
            batas = m.end()
            if sebelum and sebelum[-1] in _KATA_ALAMAT:
                continue
            nama: list[str] = []
            alamat = False
            for k in reversed(sebelum[-4:]):
                if k in _KATA_ALAMAT:
                    alamat = True  # "Jl. Mawar 3", "kos Melati kamar 5": nama tempat, bukan menu
                    break
                nama.insert(0, k)
            if alamat:
                continue
            nama = [k for k in nama if k not in _KATA_PENGISI and len(k) >= 2]
            if not nama:  # jumlah di depan: "2 risol mayo"
                sesudah = [_kata_bersih(k) for k in re.findall(r"[A-Za-z]+", segmen[m.end() :])[:4]]
                for k in sesudah:
                    if k in _KATA_ALAMAT:
                        break
                    if k not in _KATA_PENGISI and len(k) >= 2:
                        nama.append(k)
            if nama and len(" ".join(nama)) >= 4:
                calon.append(" ".join(nama))
    return calon


def _sudah_dikenal(calon: str, dikenal: list[str]) -> bool:
    """Cocok bila semua kata calon ada di satu menu, atau versi tanpa spasinya termuat (mis. "esteh" di "Es Teh Manis")."""
    kata = set(calon.split())
    ringkas = _ringkas(calon)
    for d in dikenal:
        if kata <= set(d.lower().split()) or ringkas in _ringkas(d):
            return True
    return False


def pratinjau(file_or_text: IO[bytes] | bytes | str, products: list[Product]) -> dict[str, Any]:
    """Tebakan penjual, menu terdeteksi, dan rentang tanggal. Tidak menyimpan apa pun."""
    pesan = parse_export(file_or_text, None)
    calon: list[tuple[Message, list[tuple[str, int]]]] = [(p, m) for p in pesan if (m := menu_dari_pesan(p.isi))]
    hitung = Counter(p.pengirim for p, _ in calon)
    penjual = max(hitung, key=lambda n: (hitung[n], -next(i for i, (p, _) in enumerate(calon) if p.pengirim == n))) if hitung else None

    katalog = {p.nama.strip().lower(): p for p in products}
    menu: dict[str, dict[str, Any]] = {}
    for p, daftar in calon:
        if p.pengirim != penjual:
            continue
        for nama, harga in daftar:
            kunci = nama.lower()
            ada = katalog.get(kunci)
            menu[kunci] = {"nama": ada.nama if ada else nama, "harga": harga, "sudah_ada": ada is not None, "product_id": ada.id if ada else None}

    # Menu yang disebut pembeli tapi tidak ada di daftar menu penjual maupun katalog (mungkin lupa ditambahkan).
    dikenal = [m["nama"] for m in menu.values()] + [p.nama for p in products] + [a for p in products for a in (p.alias or [])]
    sebut: dict[str, dict[str, Any]] = {}
    for p in pesan:
        if p.pengirim == penjual:
            continue
        for c in calon_menu_pembeli(p.isi):
            if _sudah_dikenal(c, dikenal):
                continue
            g = sebut.setdefault(c, {"nama": c.title(), "jumlah_sebut": 0, "contoh": p.isi if len(p.isi) <= 80 else p.isi[:80] + "…"})
            g["jumlah_sebut"] += 1
    menu_pembeli = sorted(sebut.values(), key=lambda g: (-g["jumlah_sebut"], g["nama"]))

    per_hari = Counter(p.waktu.date() for p in pesan)
    hari = sorted(per_hari)[-MAKS_HARI:]
    return {
        "penjual": penjual,
        "tanggal_awal": hari[0].isoformat() if hari else None,
        "tanggal_akhir": hari[-1].isoformat() if hari else None,
        "jumlah_pesan": sum(per_hari[h] for h in hari),
        "hari": [{"tanggal": h.isoformat(), "jumlah_pesan": per_hari[h]} for h in hari],
        "menu": list(menu.values()),
        # Tebakan kode, bukan pasti menu: ditampilkan tanpa centang dan tanpa harga, penjual yang memutuskan.
        "menu_dari_pembeli": menu_pembeli,
    }


async def impor_harian(db: Session, pemilik: str, file_or_text: bytes | str, extractor: Any = None) -> dict[str, Any]:
    """Satu batch per tanggal (tanggal_mulai = tanggal_kirim = hari itu), lalu `import_batch` untuk tiap hari.

    Saringan tanggal di `import_batch` memisah pesan per hari. Hari yang batch-nya baru dibuat dan tidak
    menghasilkan pesanan (mis. hanya obrolan penjual) dihapus lagi supaya papan tidak penuh hari kosong.
    Bila LLM gagal di tengah, hari sebelumnya sudah tersimpan dan impor ulang aman (sidik pesan).
    """
    tanggal = sorted({p.waktu.date() for p in parse_export(file_or_text, None)})[-MAKS_HARI:]
    hari: list[dict[str, Any]] = []
    total = ImportResult()
    for t in tanggal:
        batch = db.scalar(
            select(Batch).where(Batch.pemilik == pemilik, Batch.tanggal_mulai == t, Batch.tanggal_kirim == t)
        )
        baru = batch is None
        if baru:
            batch = Batch(pemilik=pemilik, nama=nama_hari(t), tanggal_mulai=t, tanggal_kirim=t)
            db.add(batch)
            db.commit()
        hasil = await import_batch(db, batch.id, file_or_text, extractor=extractor)
        punya_pesanan = db.scalar(select(Order.id).where(Order.batch_id == batch.id).limit(1)) is not None
        if baru and not punya_pesanan:
            db.delete(batch)
            db.commit()
            continue
        hari.append({"tanggal": t.isoformat(), "batch_id": batch.id, "nama": batch.nama, **hasil.model_dump()})
        for k in ImportResult.model_fields:
            setattr(total, k, getattr(total, k) + getattr(hasil, k))
    return {"hari": hari, "total": total.model_dump()}


def _status_papan(status: str) -> str:
    if status == STATUS_PERLU_CEK:
        return "perlu_cek"
    if status == STATUS_DIKIRIM:
        return "selesai"
    if status == STATUS_BATAL:
        return "batal"
    return "diproses"


def _lunas(order: Order) -> bool:
    return order.status == STATUS_DIBAYAR or any(p.dikonfirmasi for p in order.payments)


def _saran(pesan_pembeli: list[MessageRow], papan: str, lunas: bool) -> list[dict[str, str]]:
    if papan == "batal":
        return []
    saran: list[dict[str, str]] = []
    for jenis, pola, teks, perlu in (
        ("sudah_bayar", _SUDAH_BAYAR, "Pembeli bilang sudah bayar", not lunas),
        ("sudah_terima", _SUDAH_TERIMA, "Pembeli bilang sudah terima", papan != "selesai"),
    ):
        if not perlu:
            continue
        cocok = next((m for m in reversed(pesan_pembeli) if pola.search(m.isi)), None)
        if cocok is not None:
            kutipan = cocok.isi if len(cocok.isi) <= 80 else cocok.isi[:80] + "…"
            saran.append({"jenis": jenis, "teks": teks, "kutipan": kutipan})
    return saran


def ringkasan(db: Session, pemilik: str) -> dict[str, Any]:
    """Papan pesanan: keseluruhan, lalu per hari dan per jam kirim (maks 14 hari terbaru)."""
    batches = list(
        db.scalars(
            select(Batch)
            .where(Batch.pemilik == pemilik)
            .order_by(Batch.tanggal_kirim.desc(), Batch.dibuat_pada.desc())
            .limit(MAKS_HARI)
        )
    )
    nama_menu = {p.id: p.nama for p in db.scalars(select(Product).where(Product.pemilik == pemilik))}
    keseluruhan = {"perlu_cek": 0, "diproses": 0, "selesai": 0, "batal": 0, "omzet": 0, "belum_bayar": 0, "jumlah_belum_bayar": 0}
    hari = []
    for b in batches:
        orders = list(
            db.scalars(
                select(Order)
                .where(Order.batch_id == b.id)
                .options(selectinload(Order.items), selectinload(Order.customer), selectinload(Order.payments))
                .order_by(Order.jam_kirim, Order.dibuat_pada)
            )
        )
        pesan_per_pengirim: dict[str, list[MessageRow]] = {}
        for m in db.scalars(select(MessageRow).where(MessageRow.batch_id == b.id).order_by(MessageRow.waktu)):
            pesan_per_pengirim.setdefault(m.pengirim, []).append(m)

        per_jam: dict[str | None, list[dict[str, Any]]] = {}
        for o in orders:
            papan = _status_papan(o.status)
            lunas = _lunas(o)
            keseluruhan[papan] += 1
            if o.status in STATUS_DISETUJUI:
                keseluruhan["omzet"] += o.total
                if not lunas:
                    keseluruhan["belum_bayar"] += o.total
                    keseluruhan["jumlah_belum_bayar"] += 1
            per_jam.setdefault(o.jam_kirim, []).append(
                {
                    "id": o.id,
                    "nama": o.customer.nama_tampil,
                    "status": o.status,
                    "status_papan": papan,
                    "bayar": "lunas" if lunas else "belum",
                    "total": o.total,
                    "jam_kirim": o.jam_kirim,
                    "alamat": o.alamat,
                    "items": [
                        {"nama": nama_menu.get(it.product_id, it.teks_asli) if it.product_id else it.teks_asli, "qty": it.qty}
                        for it in o.items
                    ],
                    "tanda": list(o.tanda or []),
                    "saran": _saran(pesan_per_pengirim.get(o.customer.nama_tampil, []), papan, lunas),
                }
            )
        jam = sorted(per_jam, key=lambda j: (j is None, j or ""))
        hari.append(
            {
                "tanggal": b.tanggal_kirim.isoformat(),
                "batch_id": b.id,
                "nama": b.nama,
                "jam": [{"jam": j, "pesanan": per_jam[j]} for j in jam],
            }
        )
    return {"keseluruhan": keseluruhan, "hari": hari}
