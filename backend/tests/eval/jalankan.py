"""Jalankan evaluasi ke LLM sungguhan: `cd backend && python -m tests.eval.jalankan [--json hasil.json]`.

Butuh LLM_BASE_URL, LLM_API_KEY, dan LLM_MODEL di `.env`. Mencetak tabel Markdown untuk `docs/evaluasi.md`.
Tiap kasus satu panggilan (tanpa anonimisasi tambahan: pesan gold sudah bersamaran).
"""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.core.config import get_settings
from app.extractor import extract_orders
from tests.eval.skor import evaluasi, laporan_markdown, ringkas


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluasi ekstraktor ke sample/gold.json")
    ap.add_argument("--json", help="simpan hasil per kasus ke berkas ini")
    args = ap.parse_args()

    s = get_settings()
    print(f"Model: {s.llm_model or '(kosong)'}  Penyedia: {s.llm_base_url}")
    hasil = asyncio.run(evaluasi(extract_orders))
    print(laporan_markdown(hasil))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"model": s.llm_model, "ringkas": ringkas(hasil), "kasus": [asdict(h) for h in hasil]}, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
