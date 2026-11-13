"""Endpoint agen dengan agen asli dan LLM tiruan (jalur penuh: API -> agen -> tool -> DB read-only)."""

import json

from sqlalchemy.orm import Session

from app.agent import agen
from app.db import make_readonly_engine
from app.extractor import llm


def test_endpoint_agen_dengan_agen_asli_dan_llm_tiruan(client, pesanan_contoh, db_url, monkeypatch):
    engine = make_readonly_engine(db_url)
    monkeypatch.setattr(agen, "get_readonly_session", lambda: Session(engine, autoflush=False))
    giliran = [
        {"content": None, "tool_calls": [{"id": "c1", "name": "daftar_belum_bayar", "arguments": json.dumps({})}]},
        {"content": "Belum ada yang disetujui.", "tool_calls": []},
    ]

    async def chat_alat(_pesan, _alat, **_):
        return giliran.pop(0)

    monkeypatch.setattr(llm, "chat_alat", chat_alat)
    res = client.post("/api/agent/ask", json={"batch_id": "b-1", "pertanyaan": "Siapa belum bayar?", "riwayat": []})
    engine.dispose()
    assert res.status_code == 200
    assert res.json()["jawaban"] == "Belum ada yang disetujui."
    assert res.json()["trace"][0]["tool"] == "daftar_belum_bayar"
    assert res.json()["trace"][0]["argumen"] == {"batch_id": "b-1"}
