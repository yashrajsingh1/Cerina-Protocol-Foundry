from typing import Any, Dict
from langgraph.config import get_stream_writer
from app.core.llm import call_llm


def _append_note(state: Dict[str, Any], message: str, agent: str) -> None:
    notes = list(state.get("notes", []))
    notes.append(f"[{agent}] {message}")
    state["notes"] = notes


async def drafting_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Drafting Agent: Creates initial CBT protocol drafts."""
    stream = get_stream_writer()
    stream({"agent": "drafting", "event": "start", "iteration": state.get("iteration", 0)})

    intent = state["intent"]
    previous = state.get("current_draft")
    safety_score = state.get("safety_score")
    empathy_score = state.get("empathy_score")

    system_prompt = (
        "You are a CBT protocol designer. Generate concrete, structured CBT exercises "
        "(with steps, homework suggestions, and reflection prompts). Always be empathetic, "
        "non-judgmental, and avoid medical claims or crisis guidance."
    )

    refinement_note = ""
    if previous:
        refinement_note += "You are revising a previous draft based on internal reviewer feedback.\n\n"
    if safety_score is not None:
        refinement_note += f"Safety score from Safety Guardian: {safety_score:.2f}.\n"
    if empathy_score is not None:
        refinement_note += f"Empathy score from Clinical Critic: {empathy_score:.2f}.\n"

    user_prompt = (
        f"USER INTENT: {intent}\n\n"
        f"REFINEMENT CONTEXT: {refinement_note}\n\n"
        f"PREVIOUS DRAFT (if any):\n{previous or 'None'}\n\n"
        "Please produce a single CBT exercise or small protocol tailored to the intent, "
        "using clear headings and numbered steps."
    )

    draft = await call_llm(system_prompt, user_prompt)

    draft_versions = list(state.get("draft_versions", []))
    draft_versions.append(draft)

    _append_note(state, "Produced/updated draft.", "DraftingAgent")

    stream({
        "agent": "drafting",
        "event": "finish",
        "draft_preview": draft[:400],
        "version": len(draft_versions) - 1,
    })

    return {
        "current_draft": draft,
        "draft_versions": draft_versions,
        "last_agent": "drafting",
    }
