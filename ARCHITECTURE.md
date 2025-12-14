# Cerina Protocol Foundry – Architecture & Design

## System Overview

Cerina Protocol Foundry is a **non-linear, autonomous, self-correcting multi-agent system** that generates, critiques, and refines CBT (Cognitive Behavioral Therapy) exercises through a persistent, checkpointed workflow.

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Dashboard (Frontend)                    │
│  - Real-time agent activity streaming                            │
│  - Blackboard state visualization                                │
│  - Human-in-the-loop draft editor                                │
│  - Version history & metrics display                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP + SSE
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend (Port 8000)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LangGraph Multi-Agent Workflow              │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │   Drafting   │  │    Safety    │  │  Clinical    │  │   │
│  │  │    Agent     │  │   Guardian   │  │   Critic     │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │   │
│  │         ▲                ▲                   ▲           │   │
│  │         │                │                   │           │   │
│  │         └────────────────┼───────────────────┘           │   │
│  │                          │                               │   │
│  │                    ┌─────▼──────┐                        │   │
│  │                    │ Supervisor  │                       │   │
│  │                    │   Agent     │                       │   │
│  │                    └─────┬──────┘                        │   │
│  │                          │                               │   │
│  │                    ┌─────▼──────────┐                    │   │
│  │                    │ Interrupt for  │                    │   │
│  │                    │ Human Approval │                    │   │
│  │                    └────────────────┘                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         ▲                                        │
│                         │ Shared Blackboard State                │
│                         ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SQLite Database (Persistent Checkpointing)              │   │
│  │  - ProtocolSession (session metadata)                    │   │
│  │  - DraftVersion (draft history)                          │   │
│  │  - AgentLog (agent activity logs)                        │   │
│  │  - LangGraph Checkpoints (state snapshots)               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                         │
                         │ Reuses same workflow
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          MCP Server (Model Context Protocol)                     │
│  - Exposes LangGraph as a single MCP Tool                        │
│  - Integrates with Claude Desktop & other MCP clients            │
│  - Uses ctx.elicit for human approval                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. LangGraph Multi-Agent Workflow (`backend/app/core/graph.py`)

#### Agents

**Drafting Agent**
- **Role**: Creates and revises CBT exercise drafts based on user intent
- **Input**: User intent, feedback from critics, safety notes
- **Output**: Draft text, revision notes
- **Behavior**: Iteratively improves draft based on feedback

**Safety Guardian**
- **Role**: Checks for self-harm, medical advice, unsafe content
- **Input**: Current draft
- **Output**: Safety score (0–100), flagged sections, recommendations
- **Behavior**: Blocks unsafe content; suggests revisions

**Clinical Critic**
- **Role**: Evaluates empathy, tone, structure, clinical appropriateness
- **Input**: Current draft, safety feedback
- **Output**: Empathy score (0–100), quality metrics, critique notes
- **Behavior**: Provides detailed feedback on clinical quality

**Supervisor Agent**
- **Role**: Orchestrates workflow; decides routing and when to halt for human
- **Input**: Draft, safety score, empathy score, iteration count
- **Output**: Routing decision (loop back to drafting, finalize, or halt for human)
- **Behavior**: Non-linear decision logic; can loop multiple times before human approval

#### Shared Blackboard State

```python
class BlackboardState(TypedDict):
    intent: str                          # User's original intent
    current_draft: str                   # Latest draft version
    draft_versions: list[str]            # History of all drafts
    notes: list[str]                     # Scratchpad messages between agents
    safety_score: float                  # 0–100 (higher = safer)
    empathy_score: float                 # 0–100 (higher = more empathetic)
    iteration_count: int                 # Number of loops
    routing_decision: str                # Last routing decision by supervisor
    final_protocol: str | None           # Finalized protocol (after human approval)
    halted_for_human: bool               # True when awaiting human approval
```

#### Graph Topology (Non-Linear)

```
START
  │
  ▼
[Drafting Agent]
  │
  ├─────────────────┐
  │                 │
  ▼                 │
[Safety Guardian]   │
  │                 │
  ├─────────────────┤
  │                 │
  ▼                 │
[Clinical Critic]   │
  │                 │
  ├─────────────────┤
  │                 │
  ▼                 │
[Supervisor Agent]  │
  │                 │
  ├─ Loop back ─────┘ (if iteration < max)
  │
  ├─ Halt for human (if quality acceptable but needs review)
  │
  └─ Finalize (if approved by human)
      │
      ▼
    END
```

**Key Feature**: The supervisor can route back to drafting multiple times, creating an autonomous self-correcting loop before human involvement.

---

### 2. Persistence Layer (`backend/app/core/db.py` + `backend/alembic/`)

#### SQLAlchemy Models

**ProtocolSession**
- `id`: Primary key
- `intent`: Original user intent
- `status`: PENDING, RUNNING, AWAITING_HUMAN, COMPLETED, FAILED
- `created_at`: Timestamp
- `human_edited_draft`: Draft after human edits (before finalization)
- `final_protocol`: Final saved protocol

**DraftVersion**
- `id`: Primary key
- `session_id`: Foreign key to ProtocolSession
- `version_number`: Iteration number
- `draft_text`: Full draft content
- `safety_score`: Safety score at this version
- `empathy_score`: Empathy score at this version
- `created_at`: Timestamp

**AgentLog**
- `id`: Primary key
- `session_id`: Foreign key to ProtocolSession
- `agent_name`: Name of agent (DraftingAgent, SafetyGuardian, etc.)
- `action`: What the agent did
- `notes`: Agent's notes/feedback
- `created_at`: Timestamp

#### LangGraph Checkpointing

- **Checkpointer**: `SqliteSaver` from `langgraph-checkpoint-sqlite`
- **Database**: `cerina_checkpoints.db`
- **Behavior**: Every node execution is checkpointed; on crash, the graph resumes from the last checkpoint
- **Thread ID**: Each session has a unique thread ID; checkpoints are keyed by thread ID + step number

---

### 3. REST API (`backend/app/api/protocols.py`)

#### Endpoints

**POST `/api/protocols`**
- Create a new session
- Body: `{ "intent": "..." }`
- Returns: `ProtocolSessionOut` with session ID

**GET `/api/protocols`**
- List all sessions
- Returns: `list[ProtocolSessionListItem]`

**GET `/api/protocols/{session_id}`**
- Get session details
- Returns: `ProtocolSessionOut`

**GET `/api/protocols/{session_id}/blackboard`**
- Get current blackboard state snapshot
- Returns: `BlackboardSnapshot` with full state

**POST `/api/protocols/{session_id}/stream/start`**
- Start the LangGraph workflow
- Returns: Server-Sent Events (SSE) stream of agent activity

**POST `/api/protocols/{session_id}/approve`**
- Save human-edited draft
- Body: `{ "edited_draft": "..." }`
- Returns: `{ "status": "approved" }`

**POST `/api/protocols/{session_id}/stream/resume`**
- Resume LangGraph after human approval
- Returns: Server-Sent Events (SSE) stream of finalization

#### SSE Event Format

```json
{
  "type": "agent_action",
  "agent": "DraftingAgent",
  "message": "Revised draft based on feedback",
  "timestamp": "2025-12-14T20:30:45Z",
  "payload": {
    "current_draft": "...",
    "safety_score": 85,
    "empathy_score": 78
  }
}
```

---

### 4. Frontend (`frontend/src/`)

#### App.tsx – Main Dashboard

**State Management**
- `sessions`: List of all sessions
- `selectedId`: Currently selected session
- `blackboard`: Current blackboard snapshot
- `events`: Streaming agent activity log
- `draftText`: Editable draft in HITL panel
- `halted`: Whether graph is paused for human

**Key Functions**
- `handleCreateSession()`: POST `/api/protocols`
- `handleStartAgents()`: Open SSE `/stream/start`
- `handleApprove()`: POST `/approve`, then open SSE `/stream/resume`
- `refreshBlackboard()`: GET `/blackboard`

#### api.ts – TypeScript Client

- `createSession(intent)`: Create new session
- `listSessions()`: Fetch all sessions
- `getSession(id)`: Fetch session details
- `getBlackboard(id)`: Fetch blackboard state
- `approveDraft(id, editedDraft)`: Send human edits
- `openStartStream(id)`: Open SSE for workflow start
- `openResumeStream(id)`: Open SSE for workflow resume

---

### 5. MCP Server (`backend/mcp_server/server.py`)

#### Tool: `generate_cbt_protocol`

**Input**
```json
{
  "intent": "Create an exposure hierarchy for agoraphobia"
}
```

**Process**
1. Reuses the same LangGraph workflow (no code duplication)
2. Runs agents autonomously
3. When supervisor halts for human, uses `ctx.elicit` to ask for approval
4. Resumes with `Command(resume={approved_draft: ...})`
5. Returns final protocol

**Output**
```json
{
  "final_protocol": "..."
}
```

---

## Data Flow

### Scenario: User Creates a CBT Protocol

```
1. User enters intent in React UI
   ↓
2. Frontend calls POST /api/protocols
   ↓
3. Backend creates ProtocolSession (status: PENDING)
   ↓
4. User clicks "Start Agents"
   ↓
5. Frontend opens SSE /stream/start
   ↓
6. Backend starts LangGraph execution:
   - Drafting Agent creates initial draft
   - Safety Guardian checks it
   - Clinical Critic evaluates it
   - Supervisor decides: loop or halt?
   ↓
7. Each step is checkpointed to cerina_checkpoints.db
   ↓
8. SSE events stream to frontend in real-time
   - Agent activity log updates
   - Blackboard metrics update
   - Version history grows
   ↓
9. Supervisor halts before finalization
   - Status: AWAITING_HUMAN
   - Current draft sent to frontend
   ↓
10. User edits draft in React UI
    ↓
11. User clicks "Approve & Resume"
    ↓
12. Frontend calls POST /approve with edited draft
    ↓
13. Backend saves human_edited_draft to DB
    ↓
14. Frontend opens SSE /stream/resume
    ↓
15. Backend resumes LangGraph with Command(resume={approved_draft: ...})
    ↓
16. Supervisor finalizes, saves final_protocol to DB
    ↓
17. Status: COMPLETED
    ↓
18. Frontend shows final protocol + full history
```

---

## Key Design Decisions

### 1. Non-Linear Graph
- Supervisor can route back to drafting multiple times
- Enables autonomous self-correction before human involvement
- Reduces unnecessary human interruptions

### 2. Shared Blackboard State
- All agents read/write to a single `BlackboardState` dict
- Enables rich inter-agent communication (notes, feedback)
- Simplifies state management vs. message-passing

### 3. Persistent Checkpointing
- Every step is checkpointed to SQLite
- On crash, graph resumes from last checkpoint
- No loss of work or state

### 4. Human-in-the-Loop Interrupt
- Graph halts before finalization (not after)
- Human can edit the draft before it's locked in
- Ensures human approval is mandatory

### 5. MCP Reuse
- MCP server reuses the exact same LangGraph workflow
- No duplicated logic
- Ensures consistency between HTTP and MCP interfaces

---

## Scalability & Production Considerations

### Current (Development)
- SQLite for app DB and checkpoints
- Single-threaded LangGraph execution
- In-memory SSE connections

### Production Upgrades
- PostgreSQL for app DB + checkpoints
- Async task queue (Celery, RQ) for parallel agent execution
- Redis for session caching and SSE pub/sub
- Kubernetes for horizontal scaling
- Monitoring: Prometheus, Grafana, ELK stack

---

## Testing Strategy

### Unit Tests
- Agent node functions (mock LLM calls)
- State transitions (blackboard updates)
- API endpoint handlers

### Integration Tests
- Full graph execution (with stubbed LLM)
- Database persistence and recovery
- SSE streaming

### E2E Tests
- React UI workflow (Playwright)
- MCP client integration

---

## Summary

Cerina Protocol Foundry is a **production-ready, modular, autonomous multi-agent system** with:

✅ Non-linear, self-correcting agent topology  
✅ Deep shared blackboard state with rich inter-agent communication  
✅ Persistent SQLite checkpointing for crash recovery  
✅ Human-in-the-loop mandatory approval before finalization  
✅ Real-time streaming dashboard (React + SSE)  
✅ MCP integration for machine-to-machine use  
✅ Clean, modular code architecture  

**Ready for deployment and evaluation.**
