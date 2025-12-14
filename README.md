# Cerina Protocol Foundry — Local dev quick start

This repository contains a Python FastAPI backend and a React + Vite frontend. If you see "localhost refused to connect", one or both dev servers are not running.

Quick start (PowerShell on Windows):

1. Start the backend

   Open a PowerShell terminal and run:

   ```powershell
   cd "C:\Users\yashraj\Desktop\New folder (6)\backend"
   .\run_dev.ps1
   ```

   This will create a `.venv`, install `requirements.txt` and run uvicorn on `http://127.0.0.1:8000`.

2. Start the frontend

   In a second PowerShell terminal:

   ```powershell
   cd "C:\Users\yashraj\Desktop\New folder (6)\frontend"
   .\run_dev.ps1
   ```

   This runs Vite dev server (usually on `http://localhost:5173`).

3. Test endpoints

   - Backend health: `http://127.0.0.1:8000/health`
   - Frontend: open the URL printed by Vite (commonly `http://localhost:5173`).

Debugging tips

- If you get "connection refused": ensure the corresponding server terminal shows no errors and is still running.
- If package installation fails, check your Python and Node.js versions. Recommended: Python 3.10+, Node 18+.
- To check if a process is listening on a port (PowerShell):

  ```powershell
  netstat -ano | Select-String ":8000" # or :5173
  ```

Next steps

- Once both servers are running, open the frontend UI, create a session and click "Start Agents". If the UI still appears slow, I can add a background kickoff endpoint so starting is fully non-blocking.
# Cerina Protocol Foundry

Multi-agent autonomous CBT exercise generator with human-in-the-loop refinement and MCP integration.

## 1. Overview

Cerina Protocol Foundry is a **LangGraph-based multi-agent system** that designs, critiques, and refines CBT (Cognitive Behavioral Therapy) exercises.

Key properties:

- **Non-linear multi-agent architecture** (Drafting Agent, Safety Guardian, Clinical Critic, Supervisor) built with LangGraph.
- **Shared blackboard state** with draft versions, notes, metrics, and routing decisions.
- **SQLite checkpointing** for full persistence and crash-safe resume.
- **Mandatory human-in-the-loop** stage enforced via `interrupt`/`Command(resume)` in LangGraph.
- **React TypeScript dashboard** with real-time agent activity streaming, blackboard visualization, and human approval UI.
- **MCP server** exposing the workflow as a single tool consumable by MCP clients (e.g. Claude Desktop).

## 2. Tech Stack

- **Backend**: Python, FastAPI, LangGraph, SQLAlchemy (async), SQLite, Alembic.
- **LLM access**: Anthropic via `langchain-anthropic` (optional; falls back to stubbed responses if no key is provided).
- **Orchestration**: LangGraph + `langgraph-checkpoint-sqlite`.
- **Frontend**: React 18, TypeScript, Vite.
- **MCP**: `mcp` + `fastmcp` (official Python SDK).

Project root (this directory) contains two apps:

- `backend/` – FastAPI + LangGraph + MCP.
- `frontend/` – React TS dashboard.

## 3. Backend Architecture

### 3.1 Agents and Graph

Defined in `backend/app/core/graph.py`.

Agents:

- **Drafting Agent** (`drafting_agent`)
  - Generates or refines a CBT protocol draft based on the `intent` and previous drafts.
  - Incorporates previous **safety** and **empathy** scores for iterative improvement.
  - Writes into blackboard:
    - `current_draft`
    - `draft_versions` (list of all drafts)
    - `notes` (comment about what changed)

- **Safety Guardian** (`safety_guardian`)
  - Analyzes `current_draft` for self-harm content, crisis guidance, or medical advice.
  - Asks the LLM for a JSON response `{ "score": float, "explanation": string }`.
  - Writes into blackboard:
    - `safety_score`
    - `notes` (explaining the score)

- **Clinical Critic** (`clinical_critic`)
  - Evaluates empathy, clarity, structure, and likely helpfulness.
  - Asks the LLM for `{ "score": float, "explanation": string }`.
  - Writes into blackboard:
    - `empathy_score`
    - `notes` (explaining the score)

- **Supervisor / Manager** (`supervisor_agent`)
  - Orchestrates the workflow and enforces **human-in-the-loop**.
  - Reads `iteration`, `max_iterations`, `safety_score`, `empathy_score`, `current_draft`.
  - If not yet halted for human:
    - Sets `halted_for_human = True`.
    - Packages a payload containing the draft, scores, and notes.
    - Calls `interrupt(payload)` to pause the graph.
  - On resume (`Command(resume={"approved_draft": ...})`):
    - Writes `human_approved_draft` and updates `current_draft`.
    - Clears `halted_for_human`.
  - Decision policy:
    - If `(safety_score < 0.8 or empathy_score < 0.8)` and `iteration < max_iterations`:
      - Sets `decision = "iterate_again"` and routes to `drafting_agent`.
    - Else:
      - Sets `decision = "finalize"` and `final_protocol = current_draft`.

Graph topology (LangGraph):

```text
START
  → drafting_agent
  → safety_guardian
  → clinical_critic
  → supervisor_agent
      ├─ decision == "iterate_again" → drafting_agent (loop)
      └─ else → END
```

### 3.2 Shared Blackboard State

`BlackboardState` (TypedDict) contains:

- **Core**
  - `intent: str`
  - `current_draft: str`
  - `draft_versions: list[str]`
  - `notes: list[str]`
- **Metrics**
  - `safety_score: float`
  - `empathy_score: float`
  - `iteration: int`
  - `max_iterations: int`
- **Routing**
  - `last_agent: str`
  - `decision: str`
- **Human-in-the-loop**
  - `halted_for_human: bool`
  - `human_approved_draft: str | None`
- **Output**
  - `final_protocol: str | None`

This state is stored in LangGraph checkpoints and is surfaced to:

- The **React dashboard** (via `/api/protocols/{id}/blackboard` and streaming events).
- The **MCP tool**, which reads state after interrupt and after finalization.

### 3.3 Persistence and Checkpointing

- **Checkpoint DB** (LangGraph):
  - Implemented via `SqliteSaver` from `langgraph.checkpoint.sqlite`.
  - DB file path: `CERINA_CHECKPOINT_DB_PATH` (default `cerina_checkpoints.db`).
  - Every step of the graph is checkpointed keyed by `thread_id`.
  - Graph can be resumed after process restarts or crashes by invoking again with the same `thread_id` and, if needed, `Command(resume=...)`.

- **Application DB** (business data):
  - Async SQLAlchemy engine with SQLite (default `sqlite+aiosqlite:///./cerina_app.db`).
  - Models in `app/models/session.py`:
    - `ProtocolSession` (status, intent, drafts, scores, final protocol).
    - `DraftVersion` (history of drafts per session).
    - `AgentLog` (agent events).
  - Alembic configuration in `backend/alembic/` with initial migration `0001_initial.py`.

## 4. HTTP API (FastAPI)

Base URL: `http://localhost:8000/api`

Key endpoints (see `app/api/protocols.py`):

- **Create session**
  - `POST /protocols`
  - Body: `{ "intent": "Create an exposure hierarchy for agoraphobia" }`
  - Creates a new `ProtocolSession` with a fresh `thread_id`.

- **List sessions**
  - `GET /protocols` → list of `ProtocolSessionListItem`.

- **Get session**
  - `GET /protocols/{session_id}` → `ProtocolSessionOut`.

- **Inspect blackboard state**
  - `GET /protocols/{session_id}/blackboard`
  - Uses `graph.aget_state` to retrieve latest checkpoint for the session's `thread_id`.

### 4.1 Streaming and Human-in-the-Loop

Two SSE (Server-Sent Events) endpoints:

- **Start run**
  - `GET /protocols/{session_id}/stream/start`
  - Initializes blackboard:
    - `intent`, `iteration = 0`, `max_iterations = 3`, `notes = []`, `draft_versions = []`.
  - Calls `graph.astream` with `stream_mode=["custom","values","checkpoints"]`.
  - Emits JSON events of shape:

    ```jsonc
    { "type": "agent_event", "payload": { ... } }
    { "type": "state", "payload": { ...BlackboardState } }
    { "type": "halt", "payload": { "interrupts": [...] } }
    ```

  - Effects:
    - `agent_event` → stored in `AgentLog` and used in UI for visualization.
    - `state` → used to update `ProtocolSession` DB (latest draft, scores, iteration, final protocol).
    - `halt` → marks session status as `halted_for_human` and stops streaming.

- **Resume after human approval**
  - `GET /protocols/{session_id}/stream/resume`
  - Requires:
    - `ProtocolSession.status == "halted_for_human"`.
    - `human_edited_draft` set in DB.
  - Calls `graph.astream(Command(resume={"approved_draft": human_edited_draft}), ...)`.
  - Emits events identical to `/stream/start` until completion.

**Human approval endpoint**:

- `POST /protocols/{session_id}/approve`
  - Body: `{ "edited_draft": "..." }`
  - Stores `human_edited_draft` in DB.
  - Does **not** resume graph by itself; client must call `/stream/resume`.

Guarantee: The `supervisor_agent` always issues a `interrupt` before allowing finalization, so every protocol passes through a mandatory human review.

## 5. MCP Integration

Implemented in `backend/mcp_server/server.py` using the **official MCP Python SDK**.

- MCP server: `FastMCP(name="Cerina Protocol Foundry MCP")`.
- Tool: `generate_cbt_protocol(intent: str, ctx) -> str`.
- Reuses the same `get_graph()` and checkpoint DB as the HTTP backend.

Flow:

1. Create a unique `thread_id` and initial state (intent, iteration, notes, etc.).
2. Run LangGraph with `graph.astream` until an interrupt is emitted by `supervisor_agent`.
3. Read the interrupt payload containing the draft and scores.
4. Use `ctx.elicit(schema=HumanApproval)` to present the draft to the **MCP user** for edit/approval.
5. On acceptance, resume graph with `Command(resume={"approved_draft": approved_draft})`.
6. Once `final_protocol` is present in blackboard state, return it to the MCP client.

This allows, for example, **Claude Desktop** to call a single tool:

> "Ask Cerina Foundry to create a sleep hygiene protocol."

and receive a fully-reviewed protocol after a human approval interaction.

## 6. Frontend Dashboard (React + TypeScript)

Located in `frontend/` and built with Vite + React 18 + TypeScript.

Key files:

- `src/api.ts`
  - `API_BASE_URL` – defaults to `http://localhost:8000/api`.
  - REST helpers: `listSessions`, `createSession`, `getSession`, `getBlackboard`, `approveDraft`.
  - Streaming helpers: `openStartStream`, `openResumeStream` (wrap `EventSource`).

- `src/App.tsx`
  - **Session sidebar**:
    - Textarea for **intent**.
    - "Create Session" button.
    - Session list with status/time.
  - **Header controls**:
    - "Start Agents": opens SSE connection to `/stream/start`.
    - "Resume After Approval": opens SSE connection to `/stream/resume`.
  - **Blackboard panel**:
    - Renders JSON `BlackboardState`.
    - Displays `iteration`, `safety_score`, `empathy_score`.
  - **Draft panel (Human-in-the-loop)**:
    - Textarea bound to current draft (updated from `state.current_draft`).
    - Banner shows:
      - `Awaiting human approval` when graph has halted.
      - `Agents running...` when live.
    - "Approve & Resume" button:
      - `POST /approve` with edited draft.
      - Automatically calls `/stream/resume` to continue.
  - **Agent Activity panel**:
    - Shows timeline of `agent_event` payloads (`agent`, `event`, timestamp).
  - **Version History panel**:
    - Shows stored `DraftVersion` records with version index, timestamp, safety/empathy scores and full content.

The UI gives a transparent view of autonomous agents and the blackboard, while enforcing human control over finalization.

## 7. Architecture Diagram

```mermaid
flowchart TD
  subgraph Client
    UI[React TS Dashboard]
    MCPClient[Claude Desktop (MCP)]
  end

  subgraph Backend["Cerina Protocol Foundry Backend"]
    API[FastAPI\n(app/main.py)]
    DB[(SQLite\ncerina_app.db)]
    CPDB[(SQLite\ncheckpoints.db)]
    subgraph LangGraph["LangGraph Workflow\n(BlackboardState + SqliteSaver)"]
      D[Drafting Agent]
      S[Safety Guardian]
      C[Clinical Critic]
      V[Supervisor Agent]
    end
  end

  subgraph MCP["MCP Server\n(mcp_server/server.py)"]
    MCPTool[generate_cbt_protocol Tool]
  end

  UI -->|REST/SSE| API
  MCPClient -->|MCP| MCPTool

  API -->|invoke/stream\nthread_id| LangGraph
  MCPTool -->|invoke/stream\nthread_id| LangGraph

  LangGraph -->|checkpoints| CPDB
  API -->|SQLAlchemy| DB

  D --> S --> C --> V
  V -->|iterate_again| D
  V -->|interrupt\n(halt for human)| API
  UI -->|approve draft| API -->|Command(resume)| V
  MCPClient -->|HumanApproval form| MCPTool -->|Command(resume)| V
  V -->|final_protocol| LangGraph --> API --> DB
  V -->|final_protocol| LangGraph --> MCPTool --> MCPClient
```

## 8. Setup and Run Instructions

### 8.1 Backend (API + Graph + MCP)

From `backend/`:

```bash
python -m venv .venv
. .venv\\Scripts\\activate  # on Windows PowerShell

pip install -r requirements.txt

# Optional env vars (PowerShell examples)
$env:CERINA_APP_DB_URL = "sqlite+aiosqlite:///./cerina_app.db"
$env:CERINA_CHECKPOINT_DB_PATH = "cerina_checkpoints.db"
$env:CERINA_FRONTEND_ORIGIN = "http://localhost:5173"
# Optional LLM key for real Anthropic responses
# $env:ANTHROPIC_API_KEY = "<your key>"

# Run DB migrations (optional but recommended)
alembic upgrade head

# Start FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Healthcheck: `http://localhost:8000/health`.

### 8.2 Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Default URL: `http://localhost:5173`.

You may optionally create `.env` in `frontend/`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### 8.3 MCP Server (for Claude Desktop)

From `backend/` in your Python venv:

```bash
python -m mcp_server.server
```

In Claude Desktop configuration (JSON-style), register the MCP server, e.g.:

```jsonc
{
  "mcpServers": {
    "cerina-protocol-foundry": {
      "command": "python",
      "args": ["-m", "mcp_server.server"]
    }
  }
}
```

Then restart Claude and you will see the `Cerina Protocol Foundry MCP` tools.

## 9. Loom-Style Demo Script (Max ~5 Minutes)

You can use the following script to record a demo:

1. **Intro (20–30s)**
   - "Hi, this is the Cerina Protocol Foundry: a LangGraph-based multi-agent system that autonomously drafts CBT exercises, critiques them, and enforces a human approval step before anything is finalized."

2. **React Dashboard Walkthrough (2–3 min)**
   - Open `http://localhost:5173`.
   - Show the left sidebar with session creation.
   - Enter intent: `Create an exposure hierarchy for agoraphobia`.
   - Click **Create Session** and select the new session.
   - Explain the three main panels:
     - Blackboard state (JSON + scores + iteration).
     - Draft (human-in-the-loop) panel with editable text.
     - Agent activity + version history on the right.
   - Click **Start Agents**:
     - Point out agent events as they appear (Drafting, Safety, Clinical, Supervisor).
     - Show blackboard metrics updating (`iteration`, `safety_score`, `empathy_score`).
   - Wait until the run halts:
     - Highlight the banner saying `Awaiting human approval`.
     - Scroll through the draft showing what the system produced.
     - Make a small human edit to tone or wording.
   - Click **Approve & Resume**:
     - Explain that this performs `/approve` then starts `/stream/resume`, which resumes LangGraph with `Command(resume={approved_draft: ...})`.
     - Show that after a short run the `final_protocol` is set and `status` becomes `completed`.
     - Optionally show version history with earlier drafts and their scores.

3. **MCP Demo (1–1.5 min)**
   - Switch to Claude Desktop.
   - Show that the MCP server `cerina-protocol-foundry` is connected.
   - Ask Claude: `Ask Cerina Foundry to create a sleep hygiene protocol.`
   - Explain that this calls the `generate_cbt_protocol` tool:
     - It runs the same LangGraph workflow as the HTTP backend.
     - When `supervisor_agent` interrupts, Claude shows a form asking for an edited draft (this is `ctx.elicit` with `HumanApproval`).
   - Paste or edit the draft in the MCP form and submit.
   - Show that the tool resumes the graph and returns a finalized CBT protocol.

4. **Code Overview (60–90s)**
   - Briefly open `backend/app/core/graph.py`:
     - Highlight the four agents and the `interrupt(...)` usage.
     - Show how `decision` routes to another drafting loop or finalization.
   - Open `backend/app/api/protocols.py`:
     - Point at `/stream/start`, `/approve`, `/stream/resume` and describe how they integrate with `thread_id` + SQLite checkpoint DB.
   - Open `backend/mcp_server/server.py`:
     - Show `generate_cbt_protocol` reusing the same graph and using `ctx.elicit` + `Command(resume)`.
   - Summarize: "We have an autonomous, self-correcting multi-agent CBT protocol foundry with strong state hygiene, full persistence, and both human dashboard and MCP integration."

---

This repository is now **ready to deliver** as the Cerina Protocol Foundry assignment:

- Multi-agent, non-linear LangGraph architecture ✅
- Shared blackboard state with drafts, notes, metrics, and routing ✅
- SQLite checkpointing with crash-safe resume ✅
- Mandatory human-in-the-loop interrupt and resume ✅
- React TS dashboard with real-time agent visualization and approval UI ✅
- MCP server exposing the full workflow as a single tool ✅
- Alembic migration + README + architecture diagram + Loom script ✅
