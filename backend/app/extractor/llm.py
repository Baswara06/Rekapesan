"""Klien LLM kompatibel OpenAI dengan penyedia cadangan otomatis. Pemilik: Pangeran.

Penyedia utama dicoba dulu. Bila gagal (jaringan, kuota 429, galat server), penyedia cadangan dari `.env`
dipakai. Bila keduanya gagal, dilempar galat supaya orkestrasi impor membatalkan impor dan penjual bisa
mengulang. Galat 429 diprioritaskan agar API bisa menjawab `kuota_llm_habis`.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from app.core.config import Settings, get_settings

log = logging.getLogger(__name__)

TIMEOUT_DETIK = 30.0


class LLMTidakTersedia(RuntimeError):
    """Tidak ada penyedia LLM yang dikonfigurasi di `.env`."""


@dataclass(frozen=True)
class Penyedia:
    nama: str
    base_url: str
    api_key: str
    model: str


def daftar_penyedia(settings: Settings, model: str | None = None) -> list[Penyedia]:
    """Penyedia yang sudah lengkap konfigurasinya, utama dulu. `model` menimpa model utama (mis. vision)."""
    kandidat = [
        Penyedia("utama", settings.llm_base_url, settings.llm_api_key, model or settings.llm_model),
        Penyedia(
            "cadangan",
            settings.llm_fallback_base_url,
            settings.llm_fallback_api_key,
            model or settings.llm_fallback_model,
        ),
    ]
    return [p for p in kandidat if p.base_url and p.api_key and p.model]


async def _panggil(p: Penyedia, pesan: list[dict[str, Any]], max_tokens: int) -> str:
    klien = AsyncOpenAI(base_url=p.base_url, api_key=p.api_key, timeout=TIMEOUT_DETIK, max_retries=0)
    try:
        res = await klien.chat.completions.create(
            model=p.model, messages=pesan, temperature=0, max_tokens=max_tokens
        )
    finally:
        await klien.close()
    teks = res.choices[0].message.content if res.choices else None
    if not teks:
        raise RuntimeError("Penyedia mengembalikan jawaban kosong.")
    return teks


def _kuota_habis(exc: BaseException) -> bool:
    return getattr(exc, "status_code", None) == 429 or type(exc).__name__ == "RateLimitError"


async def _panggil_alat(
    p: Penyedia, pesan: list[dict[str, Any]], alat: list[dict[str, Any]] | None, max_tokens: int
) -> dict[str, Any]:
    klien = AsyncOpenAI(base_url=p.base_url, api_key=p.api_key, timeout=TIMEOUT_DETIK, max_retries=0)
    try:
        kwargs: dict[str, Any] = {"tools": alat} if alat else {}
        res = await klien.chat.completions.create(
            model=p.model, messages=pesan, temperature=0, max_tokens=max_tokens, **kwargs
        )
    finally:
        await klien.close()
    if not res.choices:
        raise RuntimeError("Penyedia mengembalikan jawaban kosong.")
    m = res.choices[0].message
    return {
        "content": m.content,
        "tool_calls": [
            {"id": t.id, "name": t.function.name, "arguments": t.function.arguments}
            for t in (m.tool_calls or [])
        ],
    }


async def _dengan_cadangan(aksi: Callable[[Penyedia], Awaitable[Any]], model: str | None) -> Any:
    """Jalankan `aksi` pada penyedia utama, lalu cadangan. Galat 429 didahulukan bila semuanya gagal."""
    penyedia = daftar_penyedia(get_settings(), model)
    if not penyedia:
        raise LLMTidakTersedia("LLM belum dikonfigurasi. Isi LLM_BASE_URL, LLM_API_KEY, dan LLM_MODEL di .env.")

    galat: list[BaseException] = []
    for p in penyedia:
        try:
            return await aksi(p)
        except Exception as exc:  # noqa: BLE001 - apa pun kegagalan penyedia memicu cadangan
            log.warning("Penyedia %s gagal: %s", p.nama, type(exc).__name__)
            galat.append(exc)
    raise next((g for g in galat if _kuota_habis(g)), galat[-1])


async def chat(pesan: list[dict[str, Any]], model: str | None = None, max_tokens: int = 1024) -> str:
    """Kirim percakapan ke penyedia utama, lalu cadangan. Kembalikan teks jawaban.

    Melempar `LLMTidakTersedia` bila tidak ada penyedia, atau galat terakhir (galat 429 didahulukan)
    bila semua penyedia gagal.
    """
    return await _dengan_cadangan(lambda p: _panggil(p, pesan, max_tokens), model)


async def chat_alat(
    pesan: list[dict[str, Any]], alat: list[dict[str, Any]] | None, max_tokens: int = 1024
) -> dict[str, Any]:
    """Seperti `chat`, tetapi dengan tool calling. Mengembalikan {"content", "tool_calls": [{id, name, arguments}]}."""
    return await _dengan_cadangan(lambda p: _panggil_alat(p, pesan, alat, max_tokens), None)
