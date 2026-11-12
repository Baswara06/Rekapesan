"""Agen tanya-jawab dengan tool read-only. Pemilik: Pangeran."""

from app.schemas import AgentAnswer


async def ask_agent(question: str, batch_id: str, history: list[dict[str, str]]) -> AgentAnswer:
    """Jawab pertanyaan penjual dengan tool calling (DB read-only) dan kembalikan trace."""
    raise NotImplementedError
