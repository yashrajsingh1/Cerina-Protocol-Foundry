from __future__ import annotations

from typing import Any, Dict

from app.core.config import get_settings

try:
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage
except Exception:  # pragma: no cover - fallback if libs missing
    ChatAnthropic = None  # type: ignore
    HumanMessage = None  # type: ignore
    SystemMessage = None  # type: ignore


settings = get_settings()


def _get_model() -> Any:
    if ChatAnthropic is None or not settings.anthropic_api_key:
        return None
    return ChatAnthropic(
        model=settings.model_name,
        api_key=settings.anthropic_api_key,
        temperature=0.3,
        max_tokens=1200,
    )


async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Simple helper around Anthropic.

    Falls back to a stubbed deterministic response if no API key/model is available
    so that the stack remains runnable in development without credentials.
    """

    model = _get_model()
    if model is None or HumanMessage is None or SystemMessage is None:
        # Fallback for local dev so the rest of the system can be exercised.
        return f"[STUBBED RESPONSE]\nSYSTEM: {system_prompt[:200]}...\nUSER: {user_prompt[:200]}...\n(Result omitted because no LLM credentials configured.)"

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    result = await model.ainvoke(messages)
    if hasattr(result, "content"):
        return str(result.content)
    return str(result)
