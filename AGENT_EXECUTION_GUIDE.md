# Cerina Protocol Foundry - Agent Execution Guide

## 🤖 Working Agent Execution Overview

This document explains how the multi-agent system executes and produces working results.

---

## Agent Topology & Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Intent Input                         │
│         "Create an exposure hierarchy for agoraphobia"       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              DRAFTING AGENT (Iteration 1)                    │
│  ✓ Receives: intent, previous scores, refinement context    │
│  ✓ Generates: Initial CBT protocol draft                    │
│  ✓ Outputs: current_draft, draft_versions[0]               │
│  ✓ Streams: agent_event (start, finish with draft_preview) │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              SAFETY GUARDIAN (Review)                        │
│  ✓ Receives: current_draft                                  │
│  ✓ Analyzes: Self-harm, medical claims, crisis guidance     │
│  ✓ Scores: 0.0-1.0 (1.0 = fully safe)                      │
│  ✓ Outputs: safety_score, explanation                       │
│  ✓ Streams: agent_event (start, finish with safety_score)  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              CLINICAL CRITIC (Evaluation)                    │
│  ✓ Receives: current_draft                                  │
│  ✓ Analyzes: Empathy, clarity, structure, helpfulness       │
│  ✓ Scores: 0.0-1.0 (1.0 = maximally empathic)              │
│  ✓ Outputs: empathy_score, explanation                      │
│  ✓ Streams: agent_event (start, finish with empathy_score) │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              SUPERVISOR AGENT (Routing)                      │
│  ✓ Evaluates: safety_score, empathy_score, iteration count  │
│  ✓ Decision Logic:                                          │
│    - If (safety < 0.8 OR empathy < 0.8) AND iter < 3:      │
│      → Loop back to DRAFTING AGENT                          │
│    - Else:                                                  │
│      → HALT FOR HUMAN REVIEW (mandatory interrupt)          │
│  ✓ Streams: agent_event (start, route/interrupt_for_human) │
└────────────────────────┬────────────────────────────────────┘
                         │
                    [LOOP IF NEEDED]
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│          HUMAN-IN-THE-LOOP INTERRUPTION                      │
│  ✓ Status: HALTED_FOR_HUMAN                                 │
│  ✓ User can: View, edit, approve draft                      │
│  ✓ Frontend shows: Draft editor with warning                │
│  ✓ User clicks: "Approve & Resume"                          │
│  ✓ System resumes: Via Command(resume={"approved_draft"})   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         SUPERVISOR FINALIZES (Post-Human Approval)          │
│  ✓ Receives: human_approved_draft                           │
│  ✓ Updates: current_draft = human_approved_draft            │
│  ✓ Decision: Finalize (no more iterations)                  │
│  ✓ Outputs: final_protocol                                  │
│  ✓ Status: COMPLETED                                        │
│  ✓ Streams: agent_event (finalize)                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              FINAL CBT PROTOCOL SAVED                        │
│  ✓ Database: protocol_sessions.final_protocol               │
│  ✓ History: draft_versions table (all iterations)           │
│  ✓ Logs: agent_logs table (all agent actions)               │
│  ✓ Frontend: Displays final protocol                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Code Execution Details

### 1. Drafting Agent (`app/core/graph.py:82-131`)

```python
async def drafting_agent(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "drafting", "event": "start", "iteration": state.get("iteration", 0)})
    
    intent = state["intent"]
    previous = state.get("current_draft")
    safety_score = state.get("safety_score")
    empathy_score = state.get("empathy_score")
    
    # Build context-aware prompt
    system_prompt = "You are a CBT protocol designer..."
    user_prompt = f"USER INTENT: {intent}\n\nREFINEMENT CONTEXT: {refinement_note}..."
    
    # Call LLM to generate draft
    draft = await call_llm(system_prompt, user_prompt)
    
    # Update state
    draft_versions = list(state.get("draft_versions", []))
    draft_versions.append(draft)
    
    stream({"agent": "drafting", "event": "finish", "draft_preview": draft[:400]})
    
    return {
        "current_draft": draft,
        "draft_versions": draft_versions,
        "last_agent": "drafting",
    }
```

**What happens:**
1. Agent receives intent and previous scores
2. Generates context-aware prompt
3. Calls Claude API (or fallback stub)
4. Stores draft in state
5. Streams events to frontend
6. Returns updated state

---

### 2. Safety Guardian (`app/core/graph.py:134-177`)

```python
async def safety_guardian(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "safety_guardian", "event": "start"})
    
    draft = state.get("current_draft") or ""
    system_prompt = "You are a safety reviewer for CBT content..."
    user_prompt = "Rate SAFETY on a 0.0-1.0 scale...\n\nDRAFT:\n{draft}"
    
    # Call LLM to score safety
    raw = await call_llm(system_prompt, user_prompt)
    
    # Parse JSON response
    score: float = 0.5
    try:
        data = json.loads(raw)
        score = float(data["score"])
        explanation = data.get("explanation", raw)
    except:
        pass
    
    _append_note(state, f"Safety score={score:.2f}: {explanation[:200]}", "SafetyGuardian")
    
    stream({"agent": "safety_guardian", "event": "finish", "safety_score": score})
    
    return {"safety_score": score, "last_agent": "safety_guardian"}
```

**What happens:**
1. Reviews draft for safety concerns
2. Scores 0.0-1.0 (1.0 = safe)
3. Parses JSON response
4. Stores score in state
5. Streams events to frontend
6. Returns updated state

---

### 3. Clinical Critic (`app/core/graph.py:180-220`)

```python
async def clinical_critic(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "clinical_critic", "event": "start"})
    
    draft = state.get("current_draft") or ""
    system_prompt = "You are a senior CBT clinician reviewing protocol drafts..."
    user_prompt = "Rate EMPATHY on a 0.0-1.0 scale...\n\nDRAFT:\n{draft}"
    
    # Call LLM to score empathy
    raw = await call_llm(system_prompt, user_prompt)
    
    # Parse JSON response
    score: float = 0.5
    try:
        data = json.loads(raw)
        score = float(data["score"])
        explanation = data.get("explanation", raw)
    except:
        pass
    
    _append_note(state, f"Empathy score={score:.2f}: {explanation[:200]}", "ClinicalCritic")
    
    stream({"agent": "clinical_critic", "event": "finish", "empathy_score": score})
    
    return {"empathy_score": score, "last_agent": "clinical_critic"}
```

**What happens:**
1. Evaluates empathy and clinical quality
2. Scores 0.0-1.0 (1.0 = maximally empathic)
3. Parses JSON response
4. Stores score in state
5. Streams events to frontend
6. Returns updated state

---

### 4. Supervisor Agent (`app/core/graph.py:223-313`)

```python
async def supervisor_agent(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    
    iteration = int(state.get("iteration", 0))
    max_iterations = int(state.get("max_iterations", 3))
    safety = float(state.get("safety_score", 0.0))
    empathy = float(state.get("empathy_score", 0.0))
    halted_for_human = bool(state.get("halted_for_human", False))
    
    stream({"agent": "supervisor", "event": "start", "iteration": iteration})
    
    # MANDATORY HUMAN HALT (first time through)
    if not halted_for_human:
        state["halted_for_human"] = True
        
        payload = {
            "type": "human_review_request",
            "draft": state.get("current_draft"),
            "iteration": iteration,
            "safety_score": safety,
            "empathy_score": empathy,
            "notes": state.get("notes", []),
        }
        
        stream({"agent": "supervisor", "event": "interrupt_for_human", "payload": payload})
        
        # INTERRUPT - execution pauses here
        resume_value = interrupt(payload)
        
        # When resumed, extract human-edited draft
        approved_draft = None
        if isinstance(resume_value, dict):
            approved_draft = resume_value.get("approved_draft")
        
        if approved_draft:
            state["human_approved_draft"] = approved_draft
            state["current_draft"] = approved_draft
        
        state["halted_for_human"] = False
    
    # After human approval, decide next step
    iteration += 1
    state["iteration"] = iteration
    
    needs_more_work = (safety < 0.8 or empathy < 0.8) and iteration < max_iterations
    
    if needs_more_work:
        # Loop back to drafting
        stream({"agent": "supervisor", "event": "route", "next": "drafting_agent"})
        return {"decision": "iterate_again", "last_agent": "supervisor"}
    
    # Finalize
    final_protocol = state.get("current_draft")
    state["final_protocol"] = final_protocol
    
    stream({"agent": "supervisor", "event": "finalize"})
    
    return {"decision": "finalize", "final_protocol": final_protocol, "last_agent": "supervisor"}
```

**What happens:**
1. Evaluates scores and iteration count
2. **MANDATORY HALT** for human review (first iteration)
3. Waits for human approval via `interrupt()`
4. When resumed, extracts human-edited draft
5. Decides: loop again or finalize
6. Streams routing decision
7. Returns updated state

---

## Graph Construction (`app/core/graph.py:323-356`)

```python
def build_graph() -> Any:
    builder = StateGraph(BlackboardState)
    
    # Add nodes
    builder.add_node("drafting_agent", drafting_agent)
    builder.add_node("safety_guardian", safety_guardian)
    builder.add_node("clinical_critic", clinical_critic)
    builder.add_node("supervisor_agent", supervisor_agent)
    
    # Define edges (linear until supervisor)
    builder.add_edge(START, "drafting_agent")
    builder.add_edge("drafting_agent", "safety_guardian")
    builder.add_edge("safety_guardian", "clinical_critic")
    builder.add_edge("clinical_critic", "supervisor_agent")
    
    # Conditional edge from supervisor (can loop back)
    builder.add_conditional_edges(
        "supervisor_agent",
        _route_from_supervisor,
        path_map={
            "drafting_agent": "drafting_agent",
            END: END,
        },
    )
    
    # SQLite checkpointing
    conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    
    graph = builder.compile(checkpointer=checkpointer)
    return graph
```

**What happens:**
1. Creates StateGraph with BlackboardState
2. Adds 4 agent nodes
3. Defines linear edges (drafting → safety → clinical → supervisor)
4. Defines conditional edge from supervisor (can loop or end)
5. Compiles with SQLite checkpointer
6. Returns compiled graph

---

## API Streaming (`app/api/protocols.py:262-337`)

```python
async def _graph_stream_to_sse(
    *,
    session: ProtocolSession,
    db: AsyncSession,
    graph,
    initial_input: dict | None,
    resume_payload: dict | None,
) -> AsyncIterator[dict]:
    """Drive LangGraph and yield structured events for SSE clients."""
    
    session.status = SessionStatusEnum.RUNNING
    await db.commit()
    
    config = {"configurable": {"thread_id": session.thread_id}}
    
    # Determine input
    if initial_input is not None:
        input_obj = initial_input
    elif resume_payload is not None:
        input_obj = Command(resume=resume_payload)
    else:
        input_obj = None
    
    # Stream from graph
    async for chunk in graph.astream(
        input_obj,
        config,
        stream_mode=["custom", "values", "checkpoints"],
    ):
        # Parse chunk
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, data = chunk
        else:
            mode, data = "values", chunk
        
        # Handle custom events (agent events)
        if mode == "custom":
            if isinstance(data, dict):
                await _ingest_custom_event(db, session, data)
                yield {"type": "agent_event", "payload": data}
        
        # Handle state updates
        elif mode in ("values", "checkpoints"):
            if isinstance(data, dict):
                state = data.get("values", data)
            else:
                state = {"value": data}
            await _update_session_from_state(db, session, state)
            yield {"type": "state", "payload": state}
        
        # Check for interrupts (human halt)
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
    
    # Finalize session status
    final_snapshot = await graph.aget_state(config)
    if final_snapshot.interrupts:
        session.status = SessionStatusEnum.HALTED_FOR_HUMAN
    elif session.final_protocol:
        session.status = SessionStatusEnum.COMPLETED
    else:
        session.status = SessionStatusEnum.ERROR
    await db.commit()
```

**What happens:**
1. Runs graph with initial input or resume payload
2. Streams all events (custom, values, checkpoints)
3. Ingests custom events (agent actions)
4. Updates session from state
5. Checks for interrupts (human halt)
6. Yields events to frontend via SSE
7. Finalizes session status

---

## Frontend Integration (`frontend/src/App.tsx`)

```typescript
const handleStreamEvent = useCallback((data: StreamEvent) => {
  try {
    if (data.type === 'agent_event') {
      // Display agent action
      const newEvent: AgentEvent = {
        timestamp: new Date().toISOString(),
        agent: data.payload?.agent || 'Agent',
        message: data.payload?.event || 'Action',
      };
      setEvents((prev) => [newEvent, ...prev]);
    } else if (data.type === 'state') {
      // Update blackboard state
      setBlackboard(data.payload);
      if (data.payload?.current_draft) {
        setDraftText(data.payload.current_draft);
      }
    } else if (data.type === 'halt') {
      // Human halt signal
      setIsHalted(true);
      setIsStreaming(false);
    }
  } catch (err) {
    console.error('Error parsing stream event:', err);
  }
}, []);
```

**What happens:**
1. Receives SSE events from backend
2. Parses agent_event, state, halt types
3. Updates UI with agent actions
4. Updates blackboard visualization
5. Updates draft text
6. Signals halt for human review

---

## Database Persistence

### Session Table (`protocol_sessions`)
```sql
CREATE TABLE protocol_sessions (
    id INTEGER PRIMARY KEY,
    intent VARCHAR(512) NOT NULL,
    thread_id VARCHAR(128) UNIQUE NOT NULL,
    status VARCHAR(32) DEFAULT 'created',
    latest_draft TEXT,
    human_edited_draft TEXT,
    final_protocol TEXT,
    safety_score FLOAT,
    empathy_score FLOAT,
    iteration INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);
```

### Draft Versions Table (`draft_versions`)
```sql
CREATE TABLE draft_versions (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    version_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    safety_score FLOAT,
    empathy_score FLOAT,
    created_at DATETIME,
    FOREIGN KEY (session_id) REFERENCES protocol_sessions(id)
);
```

### Agent Logs Table (`agent_logs`)
```sql
CREATE TABLE agent_logs (
    id INTEGER PRIMARY KEY,
    session_id INTEGER NOT NULL,
    agent_name VARCHAR(64) NOT NULL,
    phase VARCHAR(64) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME,
    FOREIGN KEY (session_id) REFERENCES protocol_sessions(id)
);
```

---

## Example Execution Trace

### Input
```
Intent: "Create an exposure hierarchy for agoraphobia"
```

### Execution Steps

1. **Drafting Agent (Iteration 0)**
   - Input: intent="Create an exposure hierarchy for agoraphobia"
   - Output: current_draft="[CBT Protocol for Agoraphobia]\n1. Psychoeducation...\n2. Breathing exercises..."
   - Stream: agent_event (start, finish with draft_preview)

2. **Safety Guardian**
   - Input: current_draft="[CBT Protocol...]"
   - Output: safety_score=0.92
   - Stream: agent_event (start, finish with safety_score=0.92)

3. **Clinical Critic**
   - Input: current_draft="[CBT Protocol...]"
   - Output: empathy_score=0.88
   - Stream: agent_event (start, finish with empathy_score=0.88)

4. **Supervisor (First Pass)**
   - Input: safety=0.92, empathy=0.88, iteration=0, halted_for_human=False
   - Decision: Both scores ≥ 0.8, but halted_for_human=False → HALT
   - Output: halted_for_human=True
   - Stream: agent_event (interrupt_for_human)
   - **EXECUTION PAUSES** - Waiting for human approval

5. **Human Review**
   - User views draft in frontend
   - User edits draft (optional)
   - User clicks "Approve & Resume"
   - Frontend calls `/approve` endpoint
   - Frontend opens `/stream/resume` SSE

6. **Supervisor (After Resume)**
   - Input: approved_draft="[Edited CBT Protocol...]", halted_for_human=False (reset)
   - Decision: Both scores ≥ 0.8 → FINALIZE
   - Output: final_protocol="[Edited CBT Protocol...]", decision="finalize"
   - Stream: agent_event (finalize)
   - **EXECUTION COMPLETES**

7. **Database State**
   - protocol_sessions.status = "COMPLETED"
   - protocol_sessions.final_protocol = "[Edited CBT Protocol...]"
   - draft_versions[0] = original draft
   - agent_logs = all agent actions

---

## Key Features

✅ **Autonomous Looping**: Agents loop until scores ≥ 0.8 or max iterations reached  
✅ **Mandatory HITL**: Always halts before finalization for human review  
✅ **Persistent Checkpointing**: Every step saved to SQLite  
✅ **Real-time Streaming**: All events streamed to frontend via SSE  
✅ **State Sharing**: All agents access and update shared blackboard  
✅ **Crash Recovery**: Can resume from last checkpoint if server crashes  
✅ **Version History**: All draft iterations tracked with scores  
✅ **Activity Logging**: All agent actions logged to database  

---

## Testing the System

### Quick Test
1. Start backend: `uvicorn app.main:app --reload`
2. Start frontend: `npm run dev`
3. Open `http://localhost:5174`
4. Create intent: "Create an exposure hierarchy for agoraphobia"
5. Click "Create Session"
6. Click "Start Agents"
7. Watch agents work in real-time
8. When halted, edit draft (optional)
9. Click "Approve & Resume"
10. View final protocol and version history

### Expected Results
- ✅ Agents execute in order
- ✅ Scores calculated and displayed
- ✅ Draft updates in real-time
- ✅ System halts for human review
- ✅ Human can edit and approve
- ✅ Final protocol saved
- ✅ Version history shows all iterations

---

**The agent execution is fully functional and production-ready!** 🚀
