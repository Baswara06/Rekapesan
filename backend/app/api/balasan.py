"""Templat balasan konfirmasi per pembeli. Pemilik: Raihan.

Dibuat kode dari templat teks, bukan LLM. Angka diambil dari pesanan yang sudah dihitung mesin aturan.
"""

from typing import Any


def rupiah(n: int) -> str:
    return "Rp" + f"{n:,}".replace(",", ".")


def _jam(jam: str | None) -> str | None:
    return jam.replace(":", ".") if jam else None


def susun_balasan(
    nama: str,
    items: list[dict[str, Any]],
    total: int,
    jam_kirim: str | None,
    alamat: str | None,
    catatan: str | None,
) -> str:
    """`items`: tiap item berisi `nama` (nama menu atau teks asli), `qty`, `harga_satuan`, `catatan_item`, `dikenal`."""
    baris = []
    for it in items:
        qty, harga = it.get("qty"), it.get("harga_satuan")
        if not isinstance(qty, int) or qty <= 0:
            teks = f"- {it['nama']} (jumlah belum jelas)"
        elif harga is None or not it.get("dikenal", True):
            teks = f"- {qty} x {it['nama']} (harga belum ada)"
        else:
            teks = f"- {qty} x {it['nama']} = {rupiah(qty * harga)}"
        if it.get("catatan_item"):
            teks += f" ({it['catatan_item']})"
        baris.append(teks)

    bagian = [f"Halo {nama}, pesanan kamu sudah kami catat ya:", *baris, f"Total: {rupiah(total)}"]
    kirim = []
    if jam_kirim:
        kirim.append(f"pukul {_jam(jam_kirim)}")
    if alamat:
        kirim.append(f"ke {alamat}")
    if kirim:
        bagian.append("Dikirim " + " ".join(kirim) + ".")
    if catatan:
        bagian.append(f"Catatan: {catatan}")
    bagian.append("Terima kasih!")
    return "\n".join(bagian)
