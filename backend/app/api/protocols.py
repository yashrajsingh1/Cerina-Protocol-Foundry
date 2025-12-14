from __future__ import annotations

import json
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from langgraph.types import Command

from app.api.deps import get_db_session, get_langgraph
from app.core.graph import new_thread_id, get_graph
from app.core.config import get_settings
from app.core.llm import call_llm
from app.core.db import AsyncSessionLocal
from app.models import ProtocolSession, DraftVersion, AgentLog, SessionStatusEnum
from app.schemas import (
    AgentLogEntry,
    DraftVersionOut,
    ProtocolSessionOut,
    ProtocolSessionListItem,
    CreateProtocolRequest,
    ApproveDraftRequest,
    BlackboardSnapshot,
)


router = APIRouter(prefix="/protocols", tags=["protocols"])
settings = get_settings()

# In-memory registry of background tasks keyed by session id. This is
# intentionally simple: tasks are not persisted across process restarts.
# For production you'd add a process supervisor or persistent job queue.
BACKGROUND_TASKS: dict[int, asyncio.Task] = {}


async def _background_run(session_id: int, initial_state: dict | None) -> None:
    """Run the LangGraph workflow for a session in the background.

    This mirrors the logic in `_graph_stream_to_sse` but writes events to the
    DB without using SSE. It allows the API to return immediately while the
    agent graph runs asynchronously.
    """
    try:
        graph = get_graph()
        async with AsyncSessionLocal() as db:
            # Load session fresh from this DB connection
            result = await db.execute(
                select(ProtocolSession).where(ProtocolSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                return

            session.status = SessionStatusEnum.RUNNING
            await db.commit()

            config = {"configurable": {"thread_id": session.thread_id}}
            initial_input = initial_state

            if initial_input is not None:
                input_obj = initial_input
            else:
                input_obj = None

            async for chunk in graph.astream(
                input_obj,
                config,
                stream_mode=["custom", "values", "checkpoints"],
            ):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, data = chunk
                else:
                    mode, data = "values", chunk

                if mode == "custom" and isinstance(data, dict):
                    await _ingest_custom_event(db, session, data)
                elif mode in ("values", "checkpoints"):
                    if isinstance(data, dict):
                        state = data.get("values", data)
                    else:
                        state = {"value": data}
                    await _update_session_from_state(db, session, state)

                latest_snapshot = await graph.aget_state(config)
                if latest_snapshot.interrupts:
                    session.status = SessionStatusEnum.HALTED_FOR_HUMAN
                    await db.commit()
                    break

            final_snapshot = await graph.aget_state(config)
            if final_snapshot.interrupts:
                session.status = SessionStatusEnum.HALTED_FOR_HUMAN
            elif session.final_protocol:
                session.status = SessionStatusEnum.COMPLETED
            else:
                session.status = SessionStatusEnum.ERROR
            await db.commit()
    except Exception:
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(ProtocolSession).where(ProtocolSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    session.status = SessionStatusEnum.ERROR
                    await db.commit()
        except Exception:
            pass



async def _load_session(db: AsyncSession, session_id: int) -> ProtocolSession:
    result = await db.execute(
        select(ProtocolSession).where(ProtocolSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _session_to_out(session: ProtocolSession) -> ProtocolSessionOut:
    return ProtocolSessionOut.from_attributes(session)


@router.post("", response_model=ProtocolSessionOut)
async def create_protocol(
    payload: CreateProtocolRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new protocol generation session.

    This only creates DB state. The actual LangGraph execution is driven by
    the streaming endpoints which use the same thread_id and checkpoint DB.
    """

    try:
        thread_id = new_thread_id()

        session = ProtocolSession(
            intent=payload.intent,
            thread_id=thread_id,
            status=SessionStatusEnum.CREATED,
            iteration=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Create an immediate placeholder/initial draft so the UI has
        # something to display right away. If an LLM is configured, try to
        # generate a quick stub draft; otherwise fall back to a simple
        # placeholder string. This makes the frontend feel more responsive
        # when users click Start.
        try:
            draft_text = await call_llm(
                "You are a CBT protocol designer (brief mode). Produce one short draft.",
                f"User intent: {payload.intent}\n\nProduce a short, structured CBT exercise in a few lines.",
            )
        except Exception as llm_err:
            print(f"LLM error (using fallback): {llm_err}")
            draft_text = f"[Queued draft for intent: {payload.intent}]"

        # Persist as an initial draft version
        draft = DraftVersion(
            session_id=session.id,
            version_index=0,
            content=draft_text,
            safety_score=None,
            empathy_score=None,
        )
        db.add(draft)
        session.latest_draft = draft_text
        await db.commit()
        await db.refresh(session)

        return _session_to_out(session)
    except Exception as e:
        print(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("", response_model=list[ProtocolSessionListItem])
async def list_sessions(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(ProtocolSession).order_by(ProtocolSession.created_at.desc()))
    sessions = result.scalars().all()
    return [ProtocolSessionListItem.from_attributes(s) for s in sessions]


@router.get("/{session_id}", response_model=ProtocolSessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db_session)):
    session = await _load_session(db, session_id)
    return _session_to_out(session)


@router.get("/{session_id}/blackboard", response_model=BlackboardSnapshot)
async def get_blackboard_state(
    session_id: int,
    db: AsyncSession = Depends(get_db_session),
    graph=Depends(get_langgraph),
):
    """Read the latest LangGraph checkpoint state for this session/thread.

    This uses LangGraph's compiled graph aget_state API, which consults the
    SQLite checkpoint DB and returns the last known blackboard state.
    """

    session = await _load_session(db, session_id)
    config = {"configurable": {"thread_id": session.thread_id}}
    snapshot = await graph.aget_state(config)

    values = snapshot.values if isinstance(snapshot.values, dict) else {"value": snapshot.values}
    created_at = getattr(snapshot, "created_at", None)

    return BlackboardSnapshot(state=values, created_at=created_at)


async def _update_session_from_state(db: AsyncSession, session: ProtocolSession, state: dict) -> None:
    session.latest_draft = state.get("current_draft") or session.latest_draft
    session.safety_score = state.get("safety_score", session.safety_score)
    session.empathy_score = state.get("empathy_score", session.empathy_score)
    session.iteration = state.get("iteration", session.iteration)
    final = state.get("final_protocol")
    if final:
        session.final_protocol = final
        session.status = SessionStatusEnum.COMPLETED
    await db.commit()


async def _ingest_custom_event(db: AsyncSession, session: ProtocolSession, event: dict) -> None:
    agent = event.get("agent", "unknown")
    phase = event.get("event", "event")
    message = json.dumps({k: v for k, v in event.items() if k not in {"agent", "event"}})

    log = AgentLog(
        session_id=session.id,
        agent_name=agent,
        phase=phase,
        message=message,
    )
    db.add(log)

    if phase == "finish" and agent == "drafting":
        draft_text = event.get("draft_preview")
        if draft_text:
            version_index = len(session.drafts)
            draft = DraftVersion(
                session_id=session.id,
                version_index=version_index,
                content=session.latest_draft or draft_text,
                safety_score=session.safety_score,
                empathy_score=session.empathy_score,
            )
            db.add(draft)

    await db.commit()


async def _graph_stream_to_sse(
    *,
    session: ProtocolSession,
    db: AsyncSession,
    graph,
    initial_input: dict | None,
    resume_payload: dict | None,
) -> AsyncIterator[dict]:
    """Drive LangGraph and yield structured events for SSE clients.

    - If initial_input is provided, start from scratch.
    - If resume_payload is provided, continue via Command(resume=...).
    Always uses the thread_id bound to this session, relying on the
    SQLite checkpointer to pick up from the previous checkpoint.
    """

    session.status = SessionStatusEnum.RUNNING
    await db.commit()

    config = {"configurable": {"thread_id": session.thread_id}}

    if initial_input is not None:
        input_obj: object = initial_input
    elif resume_payload is not None:
        input_obj = Command(resume=resume_payload)
    else:
        # Resume from latest checkpoint without new input
        input_obj = None

    async for chunk in graph.astream(
        input_obj,
        config,
        stream_mode=["custom", "values", "checkpoints"],
    ):
        # When using multiple stream modes, chunks are (mode, data)
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk
        else:
            mode, data = "values", chunk

        if mode == "custom":
            if isinstance(data, dict):
                await _ingest_custom_event(db, session, data)
                yield {"type": "agent_event", "payload": data}
        elif mode in ("values", "checkpoints"):
            if isinstance(data, dict):
                state = data.get("values", data)
            else:
                state = {"value": data}
            await _update_session_from_state(db, session, state)
            yield {"type": "state", "payload": state}

        # Interrupts are exposed via the checkpoint state under "interrupts".
        # We also check the session status to know when to stop streaming.
        latest_snapshot = await graph.aget_state(config)
        if latest_snapshot.interrupts:
            session.status = SessionStatusEnum.HALTED_FOR_HUMAN
            await db.commit()
            yield {
                "type": "halt",
                "payload": {
                    "interrupts": [i.value for i in latest_snapshot.interrupts],
                },
            }
            break

    # Re-read final state to decide if we finished.
    final_snapshot = await graph.aget_state(config)
    if final_snapshot.interrupts:
        session.status = SessionStatusEnum.HALTED_FOR_HUMAN
    elif session.final_protocol:
        session.status = SessionStatusEnum.COMPLETED
    else:
        # Execution ended without final_protocol; treat as error state.
        session.status = SessionStatusEnum.ERROR
    await db.commit()


@router.post("/{session_id}/kickoff")
async def kickoff_session(
    session_id: int,
    db: AsyncSession = Depends(get_db_session),
    graph=Depends(get_langgraph),
):
    """Kick off a background run of the agent graph for this session.

    This returns immediately (202) while the graph executes in a background
    asyncio task. Clients can then open the SSE `/stream/start` endpoint to
    subscribe to live events.
    """

    session = await _load_session(db, session_id)
    if session.status == SessionStatusEnum.RUNNING:
        return JSONResponse({"detail": "Session already running"}, status_code=400)

    initial_state = {
        "intent": session.intent,
        "iteration": session.iteration or 0,
        "max_iterations": 3,
        "notes": session.drafts and [] or [],
        "draft_versions": [],
    }

    # Start background task
    task = asyncio.create_task(_background_run(session.id, initial_state))
    BACKGROUND_TASKS[session.id] = task

    return JSONResponse({"detail": "Kickoff started"}, status_code=202)


@router.get("/{session_id}/stream/start")
async def stream_start(
    session_id: int,
    db: AsyncSession = Depends(get_db_session),
    graph=Depends(get_langgraph),
):
    """Start or restart a session from the beginning and stream events via SSE.

    This endpoint will run the graph until it either halts for human review
    (mandatory interrupt before finalization) or finishes due to error.
    """

    session = await _load_session(db, session_id)

    async def event_publisher() -> AsyncIterator[dict]:
        initial_state = {
            "intent": session.intent,
            "iteration": 0,
            "max_iterations": 3,
            "notes": [],
            "draft_versions": [],
        }
        async for event in _graph_stream_to_sse(
            session=session,
            db=db,
            graph=graph,
            initial_input=initial_state,
            resume_payload=None,
        ):
            yield json.dumps(event)

    return EventSourceResponse(event_publisher())


@router.post("/{session_id}/approve", response_model=ProtocolSessionOut)
async def approve_draft(
    session_id: int,
    payload: ApproveDraftRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Record human approval/edit and resume the graph to finalization.

    This stores the human-edited draft and then uses LangGraph's Command(resume)
    to continue execution from the supervisor node, which will either iterate
    further or finalize the protocol.
    """

    session = await _load_session(db, session_id)
    if session.status != SessionStatusEnum.HALTED_FOR_HUMAN:
        raise HTTPException(status_code=400, detail="Session is not awaiting human approval")

    # Persist human-edited draft; do not resume graph here. The frontend (or
    # any API client) should call the /stream/resume endpoint to continue
    # execution from the supervisor node.
    session.human_edited_draft = payload.edited_draft
    await db.commit()
    await db.refresh(session)
    return _session_to_out(session)


@router.get("/{session_id}/stream/resume")
async def stream_resume(
    session_id: int,
    db: AsyncSession = Depends(get_db_session),
    graph=Depends(get_langgraph),
):
    """Resume a halted session after human approval and stream events via SSE.

    This endpoint expects that /approve has already been called and that the
    human-edited draft is stored on the session. It will pass that value
    back into the LangGraph supervisor via Command(resume={"approved_draft": ...}).
    """

    session = await _load_session(db, session_id)
    if session.status != SessionStatusEnum.HALTED_FOR_HUMAN:
        raise HTTPException(status_code=400, detail="Session is not awaiting human approval")

    if not session.human_edited_draft:
        raise HTTPException(status_code=400, detail="No human-edited draft stored for this session")

    async def event_publisher() -> AsyncIterator[dict]:
        resume_payload = {"approved_draft": session.human_edited_draft}
        async for event in _graph_stream_to_sse(
            session=session,
            db=db,
            graph=graph,
            initial_input=None,
            resume_payload=resume_payload,
        ):
            yield json.dumps(event)

    return EventSourceResponse(event_publisher())
