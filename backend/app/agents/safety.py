import json
from typing import Any, Dict
from langgraph.config import get_stream_writer
from app.core.llm import call_llm


def _append_note(state: Dict[str, Any], message: str, agent: str) -> None:
    notes = list(state.get("notes", []))
    notes.append(f"[{agent}] {message}")
    state["notes"] = notes


async def safety_guardian(state: Dict[str, Any]) -> Dict[str, Any]:
    """Safety Guardian: Reviews draft for safety concerns."""
    stream = get_stream_writer()
    stream({"agent": "safety_guardian", "event": "start"})

    draft = state.get("current_draft") or ""
    system_prompt = (
        "You are a safety reviewer for CBT content. Your job is to rate whether the text "
        "contains: self-harm instructions, crisis guidance, medical/diagnostic claims, "
        "or other unsafe material."
    )
    user_prompt = (
        "Rate SAFETY on a 0.0-1.0 scale, where 1.0 is fully safe and appropriate. "
        "Only respond with a JSON object like {\"score\": float, \"explanation\": string}.\n\n"
        f"DRAFT:\n{draft}"
    )

    raw = await call_llm(system_prompt, user_prompt)

    score: float = 0.5
    explanation = raw
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "score" in data:
            score = float(data["score"])
            explanation = data.get("explanation", explanation)
    except Exception:
        pass

    _append_note(state, f"Safety score={score:.2f}: {explanation[:200]}", "SafetyGuardian")

    stream({
        "agent": "safety_guardian",
        "event": "finish",
        "safety_score": score,
    })

    return {
        "safety_score": score,
        "last_agent": "safety_guardian",
    }
