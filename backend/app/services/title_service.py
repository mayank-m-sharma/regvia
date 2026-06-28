"""NLP title generation for chat sessions."""

from __future__ import annotations

from openai import AsyncOpenAI

from app.core.settings import settings

_TITLE_PROMPT = (
    "Generate a concise title (5 words or fewer) for a compliance chat session"
    " based on this Q&A exchange. Return ONLY the title text, no punctuation at"
    " the end, no quotes.\n\n"
    "Question: {question}\n"
    "Answer: {answer}"
)


def _get_llm_client() -> tuple[AsyncOpenAI, str]:
    if settings.OPENAI_API_KEY:
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY), settings.OPENAI_CHAT_MODEL
    if settings.APP_ENV == "local":
        client = AsyncOpenAI(
            base_url=f"{settings.OLLAMA_BASE_URL}/v1",
            api_key="ollama",
        )
        return client, settings.OLLAMA_CHAT_MODEL
    raise RuntimeError("No LLM provider configured for title generation.")


async def generate_session_title(question: str, answer: str) -> str:
    """Generate a short NLP title from the first Q&A exchange.

    Falls back to the first 60 characters of the question on any error.
    """
    fallback = (question[:57] + "…") if len(question) > 60 else question
    try:
        client, model = _get_llm_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": _TITLE_PROMPT.format(
                        question=question[:500],
                        answer=answer[:500],
                    ),
                }
            ],
            max_tokens=20,
            temperature=0.3,
        )
        raw = (response.choices[0].message.content or "").strip()
        title = raw.strip('"').strip("'")
        return title if title else fallback
    except Exception:  # noqa: BLE001
        return fallback
