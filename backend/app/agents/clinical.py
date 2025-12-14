import json
from typing import Any, Dict
from langgraph.config import get_stream_writer
from app.core.llm import call_llm


def _append_note(state: Dict[str, Any], message: str, agent: str) -> None:
    notes = list(state.get("notes", []))
    notes.append(f"[{agent}] {message}")
    state["notes"] = notes


async def clinical_critic(state: Dict[str, Any]) -> Dict[str, Any]:
    """Clinical Critic: Evaluates empathy and clinical quality."""
    stream = get_stream_writer()
    stream({"agent": "clinical_critic", "event": "start"})

    draft = state.get("current_draft") or ""
    system_prompt = (
        "You are a senior CBT clinician reviewing protocol drafts. Evaluate empathy, "
        "clarity, structure, and likely helpfulness for a typical client."
    )
    user_prompt = (
        "Rate EMPATHY on a 0.0-1.0 scale, where 1.0 is maximally empathic and supportive. "
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

    _append_note(state, f"Empathy score={score:.2f}: {explanation[:200]}", "ClinicalCritic")

    stream({
        "agent": "clinical_critic",
        "event": "finish",
        "empathy_score": score,
    })

    return {
        "empathy_score": score,
        "last_agent": "clinical_critic",
    }
