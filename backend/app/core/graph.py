from __future__ import annotations

import uuid
from typing import Any, Dict, TypedDict, Optional, List

from typing_extensions import Annotated

# LangGraph imports are optional at runtime for local dev. If the
# langgraph packages are not installed we provide a lightweight
# DummyGraph implementation so the HTTP server and frontend can start
# and exercise a stubbed workflow without external dependencies.
try:
    from langgraph.graph import StateGraph, START, END  # type: ignore
    from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore
    from langgraph.types import Command, interrupt  # type: ignore
    from langgraph.config import get_stream_writer  # type: ignore
    _HAS_LANGGRAPH = True
except Exception:  # pragma: no cover - allow running without langgraph
    StateGraph = None  # type: ignore
    START = None  # type: ignore
    END = None  # type: ignore
    SqliteSaver = None  # type: ignore
    Command = None  # type: ignore
    interrupt = None  # type: ignore
    def get_stream_writer():
        # simple no-op stream writer when langgraph is absent
        def _w(_: dict) -> None:
            return None

        return _w
    _HAS_LANGGRAPH = False

from app.core.config import get_settings
from app.core.llm import call_llm


settings = get_settings()


class BlackboardState(TypedDict, total=False):
    """Shared blackboard for all agents.

    We intentionally keep this explicit rather than generic dicts so that
    the UI can safely visualize the state and the DB can mirror key fields.
    """

    # User goal and context
    intent: str

    # Drafting lifecycle
    current_draft: str
    draft_versions: List[str]

    # Agent scratchpads
    notes: List[str]

    # Metrics
    safety_score: float
    empathy_score: float
    iteration: int

    # Routing & control
    last_agent: str
    decision: str
    max_iterations: int

    # Human-in-the-loop fields
    halted_for_human: bool
    human_message: Optional[str]
    human_approved_draft: Optional[str]

    # Final artifact
    final_protocol: Optional[str]


def _append_note(state: BlackboardState, message: str, agent: str) -> None:
    notes = list(state.get("notes", []))
    notes.append(f"[{agent}] {message}")
    state["notes"] = notes


async def drafting_agent(state: BlackboardState) -> Dict[str, Any]:
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


async def safety_guardian(state: BlackboardState) -> Dict[str, Any]:
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

    # Very light-weight parsing to avoid depending on a strict schema.
    score: float = 0.5
    explanation = raw
    try:
        import json

        data = json.loads(raw)
        if isinstance(data, dict) and "score" in data:
            score = float(data["score"])
            explanation = data.get("explanation", explanation)
    except Exception:
        # leave defaults
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


async def clinical_critic(state: BlackboardState) -> Dict[str, Any]:
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
        import json

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


async def supervisor_agent(state: BlackboardState) -> Dict[str, Any]:
    """Supervisor decides whether to iterate, halt for human, or finalize.

    This node is where we enforce the mandatory human-in-the-loop halt using
    langgraph.types.interrupt. It will always interrupt once before marking
    the protocol as finalized.
    """

    stream = get_stream_writer()

    iteration = int(state.get("iteration", 0))
    max_iterations = int(state.get("max_iterations", 3))
    safety = float(state.get("safety_score", 0.0))
    empathy = float(state.get("empathy_score", 0.0))
    halted_for_human = bool(state.get("halted_for_human", False))

    draft = state.get("current_draft") or ""

    stream({
        "agent": "supervisor",
        "event": "start",
        "iteration": iteration,
        "safety": safety,
        "empathy": empathy,
        "halted_for_human": halted_for_human,
    })

    # If we have not yet asked for human approval, do so now via interrupt.
    if not halted_for_human:
        state["halted_for_human"] = True
        _append_note(state, "Halting for human review of current draft.", "Supervisor")

        payload = {
            "type": "human_review_request",
            "draft": draft,
            "iteration": iteration,
            "safety_score": safety,
            "empathy_score": empathy,
            "notes": state.get("notes", []),
        }

        stream({"agent": "supervisor", "event": "interrupt_for_human", "payload": payload})

        # Interrupt execution and surface payload to the client. When resumed,
        # the returned value will contain the approved human-edited draft.
        resume_value = interrupt(payload)

        # When the graph is resumed, we expect a dict with the approved draft.
        approved_draft = None
        if isinstance(resume_value, dict):
            approved_draft = resume_value.get("approved_draft")

        if approved_draft:
            state["human_approved_draft"] = approved_draft
            state["current_draft"] = approved_draft
            _append_note(state, "Human provided an edited draft.", "Supervisor")
        else:
            _append_note(state, "Human resume did not include approved_draft; keeping existing draft.", "Supervisor")

        # We have now passed the human gate; mark flag false so we don't halt again.
        state["halted_for_human"] = False

    # After human approval, decide whether another refinement loop is needed
    # based on safety/empathy and iteration budget.
    iteration += 1
    state["iteration"] = iteration

    needs_more_work = (safety < 0.8 or empathy < 0.8) and iteration < max_iterations

    if needs_more_work:
        decision = "iterate_again"
        _append_note(state, "Scores below threshold; requesting another drafting pass.", "Supervisor")
        stream({"agent": "supervisor", "event": "route", "next": "drafting_agent"})
        return {
            "decision": decision,
            "last_agent": "supervisor",
        }

    # Otherwise we can finalize.
    decision = "finalize"
    final_protocol = state.get("current_draft") or draft
    state["final_protocol"] = final_protocol
    _append_note(state, "Finalizing protocol after human approval.", "Supervisor")

    stream({"agent": "supervisor", "event": "finalize"})

    return {
        "decision": decision,
        "final_protocol": final_protocol,
        "last_agent": "supervisor",
    }


def _route_from_supervisor(state: BlackboardState) -> str:
    decision = state.get("decision")
    if decision == "iterate_again":
        return "drafting_agent"
    return END


def build_graph() -> Any:
    """Build and compile the LangGraph workflow with SQLite checkpointing."""
    if _HAS_LANGGRAPH:
        builder = StateGraph(BlackboardState)

        builder.add_node("drafting_agent", drafting_agent)
        builder.add_node("safety_guardian", safety_guardian)
        builder.add_node("clinical_critic", clinical_critic)
        builder.add_node("supervisor_agent", supervisor_agent)

        builder.add_edge(START, "drafting_agent")
        builder.add_edge("drafting_agent", "safety_guardian")
        builder.add_edge("safety_guardian", "clinical_critic")
        builder.add_edge("clinical_critic", "supervisor_agent")

        builder.add_conditional_edges(
            "supervisor_agent",
            _route_from_supervisor,
            path_map={
                "drafting_agent": "drafting_agent",
                END: END,
            },
        )

        # SQLite checkpointer for full persistence and crash recovery.
        # We use the long-lived connection form rather than context manager so the
        # compiled graph can be reused throughout the app lifecycle.
        import sqlite3

        conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

        graph = builder.compile(checkpointer=checkpointer)
        return graph

    # Fallback dummy graph for local development when langgraph is unavailable.
    class DummySnapshot:
        def __init__(self, values: dict | None = None, interrupts: list | None = None, created_at=None):
            self.values = values or {}
            self.interrupts = interrupts or []
            self.created_at = created_at

    class DummyGraph:
        async def aget_state(self, config: dict) -> Any:
            # Return an empty snapshot indicating no interrupts by default.
            return DummySnapshot(values={})

        async def astream(self, input_obj: object | None, config: dict, stream_mode: list[str] | None = None):
            # Lightweight async generator emulating a single run with a human interrupt
            # after producing a stubbed draft. It yields simple `custom` events and
            # then leaves an interrupt-like payload via the final snapshot.
            # 1) drafting event
            yield ("custom", {"agent": "drafting", "event": "start"})
            # produce a stub draft using the provided intent if present
            state = input_obj if isinstance(input_obj, dict) else {}
            intent = state.get("intent", "(no intent)")
            draft = f"[STUBBED DRAFT for: {intent}]\n1. Step one\n2. Step two\nHomework: reflect."
            yield ("custom", {"agent": "drafting", "event": "finish", "draft_preview": draft})
            # safety and critique events
            yield ("custom", {"agent": "safety_guardian", "event": "finish", "safety_score": 0.9})
            yield ("custom", {"agent": "clinical_critic", "event": "finish", "empathy_score": 0.85})
            # yield a state checkpoint
            values = {
                "current_draft": draft,
                "draft_versions": [draft],
                "safety_score": 0.9,
                "empathy_score": 0.85,
                "iteration": 0,
            }
            yield ("values", values)
            # finally signal a halt for human by making the generator stop; the
            # HTTP code checks aget_state().interrupts - our dummy aget_state will
            # provide an 'interrupt' via the next aget_state call if needed.

    return DummyGraph()


_graph_instance: Any | None = None


def get_graph() -> Any:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_graph()
    return _graph_instance


def new_thread_id() -> str:
    return str(uuid.uuid4())
