from __future__ import annotations

import asyncio
import pathlib
import sys
import uuid
from typing import Optional

from pydantic import BaseModel, Field

# Ensure the backend package is importable when running this file directly.
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from langgraph.types import Command

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

from app.core.graph import get_graph


mcp = FastMCP(name="Cerina Protocol Foundry MCP")


class HumanApproval(BaseModel):
    """Schema for human approval of a CBT draft inside MCP."""

    approved_draft: str = Field(
        description=(
            "Edited CBT protocol draft. Please review the proposed exercise, "
            "make any human-level clinical adjustments you deem necessary, and "
            "paste the final version here."
        )
    )


@mcp.tool()
async def generate_cbt_protocol(
    intent: str,
    ctx: Context[ServerSession, None],
) -> str:
    """Generate a CBT protocol for the given intent with mandatory human approval.

    This tool runs the same LangGraph workflow used by the HTTP backend:
    - Drafting Agent creates an initial CBT exercise.
    - Safety Guardian and Clinical Critic evaluate safety and empathy.
    - Supervisor halts with an interrupt and surfaces the draft.
    - This tool then elicits human approval via MCP forms.
    - After human edits, the graph is resumed to finalize the protocol.
    """

    graph = get_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Initial blackboard input mirrors the HTTP backend.
    initial_state = {
        "intent": intent,
        "iteration": 0,
        "max_iterations": 3,
        "notes": [],
        "draft_versions": [],
    }

    # Run until the supervisor interrupts for human approval.
    await ctx.info("Starting Cerina Protocol Foundry workflow (draft + internal review)...")

    async for _ in graph.astream(
        initial_state,
        config,
        stream_mode=["values", "checkpoints"],
    ):
        snapshot = await graph.aget_state(config)
        if snapshot.interrupts:
            break

    snapshot = await graph.aget_state(config)
    if not snapshot.interrupts:
        raise RuntimeError("Expected human interrupt but none was recorded in the checkpoint.")

    # Extract the draft and metadata from the interrupt payload.
    interrupt = snapshot.interrupts[0]
    payload = interrupt.value if isinstance(interrupt.value, dict) else {"draft": str(interrupt.value)}

    draft_text: str = payload.get("draft") or payload.get("current_draft") or "(no draft in interrupt payload)"
    safety_score: Optional[float] = payload.get("safety_score")
    empathy_score: Optional[float] = payload.get("empathy_score")

    details_lines = ["A CBT draft is ready for review."]
    if safety_score is not None:
        details_lines.append(f"Safety score: {safety_score:.2f}")
    if empathy_score is not None:
        details_lines.append(f"Empathy score: {empathy_score:.2f}")

    await ctx.info("Halting for human clinical review via MCP elicitation.")

    result = await ctx.elicit(
        message=(
            "Please review and clinically refine the following CBT protocol draft.\n\n"
            + "\n".join(details_lines)
            + "\n\n--- DRAFT BEGIN ---\n"
            + draft_text
            + "\n--- DRAFT END ---\n\n"
            + "You may adjust tone, wording, or structure, but please keep the CBT framing."
        ),
        schema=HumanApproval,
    )

    if result.action != "accept" or not result.data:
        raise RuntimeError("Human approval was declined or cancelled; protocol cannot be finalized.")

    approved_draft = result.data.approved_draft

    await ctx.info("Human-edited draft received. Resuming LangGraph workflow to finalize protocol...")

    resume_cmd = Command(resume={"approved_draft": approved_draft})

    async for _ in graph.astream(
        resume_cmd,
        config,
        stream_mode=["values", "checkpoints"],
    ):
        pass

    final_snapshot = await graph.aget_state(config)
    state = final_snapshot.values if isinstance(final_snapshot.values, dict) else {"value": final_snapshot.values}
    final_protocol = state.get("final_protocol") or state.get("current_draft")

    if not final_protocol:
        raise RuntimeError("Graph completed without producing a final_protocol.")

    await ctx.info("Cerina Protocol Foundry workflow completed.")
    return final_protocol


if __name__ == "__main__":  # pragma: no cover - manual server launch
    from mcp.server.stdio import stdio_server

    stdio_server(mcp).run()
