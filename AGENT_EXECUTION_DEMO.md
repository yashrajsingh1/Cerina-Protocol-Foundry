# Agent Execution Demonstration - Complete Workflow

## ✅ System Status

**Backend:** Running on `http://localhost:8000`
- Application startup complete
- Uvicorn server active
- Database initialized

**Frontend:** Running on `http://localhost:5174`
- Vite dev server ready
- React dashboard loaded
- API connected to backend

---

## 🤖 Agent Execution Flow - Where Agents Work

### Agent 1: Drafting Agent
**Location:** `backend/app/core/graph.py:83-132`

**What it does:**
- Receives user intent
- Generates initial CBT protocol draft
- Incorporates previous safety/empathy scores for refinement
- Updates blackboard state with `current_draft` and `draft_versions`

**Output:**
```
Agent: drafting
Event: start (iteration 0)
Event: finish (draft_preview: first 400 chars of draft)
```

**Code Execution:**
```python
async def drafting_agent(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "drafting", "event": "start", "iteration": state.get("iteration", 0)})
    
    # Generate draft using LLM
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

---

### Agent 2: Safety Guardian
**Location:** `backend/app/core/graph.py:135-178`

**What it does:**
- Reviews draft for safety concerns
- Scores safety on 0.0-1.0 scale (1.0 = fully safe)
- Checks for: self-harm, crisis guidance, medical claims
- Updates blackboard with `safety_score`

**Output:**
```
Agent: safety_guardian
Event: start
Event: finish (safety_score: 0.92)
```

**Code Execution:**
```python
async def safety_guardian(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "safety_guardian", "event": "start"})
    
    draft = state.get("current_draft") or ""
    
    # Score safety using LLM
    raw = await call_llm(system_prompt, user_prompt)
    
    # Parse JSON response
    score = float(data["score"])  # 0.0-1.0
    
    stream({"agent": "safety_guardian", "event": "finish", "safety_score": score})
    
    return {"safety_score": score, "last_agent": "safety_guardian"}
```

---

### Agent 3: Clinical Critic
**Location:** `backend/app/core/graph.py:181-221`

**What it does:**
- Evaluates empathy and clinical quality
- Scores empathy on 0.0-1.0 scale (1.0 = maximally empathic)
- Checks: tone, clarity, structure, helpfulness
- Updates blackboard with `empathy_score`

**Output:**
```
Agent: clinical_critic
Event: start
Event: finish (empathy_score: 0.88)
```

**Code Execution:**
```python
async def clinical_critic(state: BlackboardState) -> Dict[str, Any]:
    stream = get_stream_writer()
    stream({"agent": "clinical_critic", "event": "start"})
    
    draft = state.get("current_draft") or ""
    
    # Score empathy using LLM
    raw = await call_llm(system_prompt, user_prompt)
    
    # Parse JSON response
    score = float(data["score"])  # 0.0-1.0
    
    stream({"agent": "clinical_critic", "event": "finish", "empathy_score": score})
    
    return {"empathy_score": score, "last_agent": "clinical_critic"}
```

---

### Agent 4: Supervisor Agent
**Location:** `backend/app/core/graph.py:224-314`

**What it does:**
- Orchestrates workflow routing
- Evaluates scores and iteration count
- Decides: loop back to drafting or halt for human
- Enforces mandatory human-in-the-loop interrupt
- Finalizes protocol after human approval

**Decision Logic:**
```python
needs_more_work = (safety < 0.8 or empathy < 0.8) and iteration < max_iterations

if needs_more_work:
    # Loop back to Drafting Agent
    decision = "iterate_again"
    return "drafting_agent"
else:
    # Halt for human review
    decision = "finalize"
    interrupt(payload)  # Mandatory human approval
```

**Output:**
```
Agent: supervisor
Event: start (iteration, safety, empathy scores)
Event: interrupt_for_human (payload with draft, scores, notes)
Event: finalize (after human approval)
```

---

## 📊 Graph Topology - How Agents Connect

**Location:** `backend/app/core/graph.py:324-356`

```
START
  ↓
[Drafting Agent]
  ↓
[Safety Guardian]
  ↓
[Clinical Critic]
  ↓
[Supervisor Agent]
  ├─ Decision: iterate_again? → Loop back to Drafting Agent
  └─ Decision: finalize? → END (with human approval)
```

**Code:**
```python
def build_graph() -> Any:
    builder = StateGraph(BlackboardState)
    
    # Add nodes
    builder.add_node("drafting_agent", drafting_agent)
    builder.add_node("safety_guardian", safety_guardian)
    builder.add_node("clinical_critic", clinical_critic)
    builder.add_node("supervisor_agent", supervisor_agent)
    
    # Linear edges
    builder.add_edge(START, "drafting_agent")
    builder.add_edge("drafting_agent", "safety_guardian")
    builder.add_edge("safety_guardian", "clinical_critic")
    builder.add_edge("clinical_critic", "supervisor_agent")
    
    # Conditional edge (looping)
    builder.add_conditional_edges(
        "supervisor_agent",
        _route_from_supervisor,
        path_map={
            "drafting_agent": "drafting_agent",
            END: END,
        },
    )
    
    # Compile with SQLite checkpointing
    graph = builder.compile(checkpointer=checkpointer)
    return graph
```

---

## 🔄 Complete Agent Execution Example

### Input
```
Intent: "Create an exposure hierarchy for agoraphobia"
```

### Execution Steps

**Step 1: Drafting Agent (Iteration 0)**
- Input: intent, max_iterations=3, iteration=0
- Action: Generate initial CBT protocol draft
- Output: 
  ```
  current_draft: "[CBT Protocol for Agoraphobia]\n1. Psychoeducation...\n2. Breathing exercises..."
  draft_versions: ["[CBT Protocol...]"]
  ```
- Stream Event:
  ```json
  {"agent": "drafting", "event": "start", "iteration": 0}
  {"agent": "drafting", "event": "finish", "draft_preview": "[CBT Protocol...]"}
  ```

**Step 2: Safety Guardian**
- Input: current_draft
- Action: Score safety (0.0-1.0)
- Output:
  ```
  safety_score: 0.92
  notes: ["[SafetyGuardian] Safety score=0.92: No harmful content detected"]
  ```
- Stream Event:
  ```json
  {"agent": "safety_guardian", "event": "start"}
  {"agent": "safety_guardian", "event": "finish", "safety_score": 0.92}
  ```

**Step 3: Clinical Critic**
- Input: current_draft
- Action: Score empathy (0.0-1.0)
- Output:
  ```
  empathy_score: 0.88
  notes: ["[ClinicalCritic] Empathy score=0.88: Good tone and structure"]
  ```
- Stream Event:
  ```json
  {"agent": "clinical_critic", "event": "start"}
  {"agent": "clinical_critic", "event": "finish", "empathy_score": 0.88}
  ```

**Step 4: Supervisor Agent**
- Input: safety=0.92, empathy=0.88, iteration=0
- Evaluation: Both scores ≥ 0.8, but halted_for_human=False
- Decision: HALT for human review (mandatory)
- Output:
  ```
  halted_for_human: True
  interrupt_payload: {
    "type": "human_review_request",
    "draft": "[CBT Protocol...]",
    "iteration": 0,
    "safety_score": 0.92,
    "empathy_score": 0.88,
    "notes": [...]
  }
  ```
- Stream Event:
  ```json
  {"agent": "supervisor", "event": "start", "iteration": 0, "safety": 0.92, "empathy": 0.88}
  {"agent": "supervisor", "event": "interrupt_for_human", "payload": {...}}
  ```

**Step 5: Human Review (Frontend)**
- Frontend receives halt signal
- Shows "⚠️ Awaiting Approval"
- User can edit draft
- User clicks "Approve & Resume"

**Step 6: Supervisor Finalizes (After Resume)**
- Input: human_approved_draft (from user)
- Update: current_draft = human_approved_draft
- Decision: FINALIZE (no more iterations)
- Output:
  ```
  final_protocol: "[Edited CBT Protocol...]"
  status: "COMPLETED"
  ```
- Stream Event:
  ```json
  {"agent": "supervisor", "event": "finalize"}
  ```

---

## 📍 Where to See Agents Working in Frontend

### 1. Agent Activity Panel (Right Side)
**Location:** `frontend/src/App.tsx:316-337`

Shows real-time agent events:
```
drafting - start (Iteration 0)
drafting - finish (draft_preview: "[CBT Protocol...]")
safety_guardian - start
safety_guardian - finish (safety_score: 0.92)
clinical_critic - start
clinical_critic - finish (empathy_score: 0.88)
supervisor - start
supervisor - interrupt_for_human
```

### 2. Blackboard State Panel (Left Side)
**Location:** `frontend/src/App.tsx:271-284`

Shows real-time state updates:
```json
{
  "intent": "Create an exposure hierarchy for agoraphobia",
  "current_draft": "[CBT Protocol...]",
  "draft_versions": ["[CBT Protocol...]"],
  "safety_score": 0.92,
  "empathy_score": 0.88,
  "iteration": 0,
  "notes": [
    "[DraftingAgent] Produced/updated draft.",
    "[SafetyGuardian] Safety score=0.92: ...",
    "[ClinicalCritic] Empathy score=0.88: ...",
    "[Supervisor] Halting for human review..."
  ]
}
```

### 3. Draft Panel (Human-in-the-Loop)
**Location:** `frontend/src/App.tsx:286-311`

Shows:
- Current draft being generated/refined
- Status: "Idle" → "⚙️ Running" → "⚠️ Awaiting Approval"
- Editable when halted
- "Approve & Resume" button when ready

### 4. Version History Panel (Right Side)
**Location:** `frontend/src/App.tsx:339-356`

Shows all draft iterations with scores:
```
v0 • S: 0.92 E: 0.88
  [CBT Protocol for Agoraphobia...]
```

---

## 🔌 API Endpoints Where Agents Execute

### 1. Create Session
**Endpoint:** `POST /api/protocols`
**Location:** `backend/app/api/protocols.py:134-183`
- Creates session in database
- Initializes blackboard state
- Ready for agent execution

### 2. Start Agents (SSE Streaming)
**Endpoint:** `GET /api/protocols/{id}/stream/start`
**Location:** `backend/app/api/protocols.py:372-403`
- Initializes blackboard with intent
- Calls `graph.astream()` with all agents
- Streams events in real-time to frontend
- Agents execute sequentially: Drafting → Safety → Clinical → Supervisor

### 3. Approve Draft
**Endpoint:** `POST /api/protocols/{id}/approve`
**Location:** `backend/app/api/protocols.py:406-429`
- Saves human-edited draft
- Stores in database

### 4. Resume After Approval (SSE Streaming)
**Endpoint:** `GET /api/protocols/{id}/stream/resume`
**Location:** `backend/app/api/protocols.py:432-463`
- Resumes graph from supervisor node
- Uses `Command(resume={"approved_draft": ...})`
- Supervisor finalizes protocol
- Streams completion events

---

## 🧪 Test Workflow to See Agents Working

### Step 1: Create Session
```
Frontend: Type "Create an exposure hierarchy for agoraphobia"
Frontend: Click "Create Session"
Backend: POST /api/protocols → Creates session in database
Result: Session appears in Sessions list
```

### Step 2: Start Agents
```
Frontend: Click on session to select it
Frontend: Click "Start Agents"
Backend: GET /api/protocols/{id}/stream/start → Starts agent execution
Agents: Execute in sequence (Drafting → Safety → Clinical → Supervisor)
Frontend: Real-time updates in Agent Activity and Blackboard panels
```

### Step 3: Monitor Agent Execution
```
Watch Agent Activity panel:
- drafting: start
- drafting: finish (with draft preview)
- safety_guardian: start
- safety_guardian: finish (with safety_score)
- clinical_critic: start
- clinical_critic: finish (with empathy_score)
- supervisor: start
- supervisor: interrupt_for_human (HALT)

Watch Blackboard State panel:
- current_draft updates with agent-generated text
- safety_score updates (0.0-1.0)
- empathy_score updates (0.0-1.0)
- iteration count increases
- notes accumulate with agent messages
```

### Step 4: Human Review
```
Frontend: Status shows "⚠️ Awaiting Approval"
Frontend: Draft is editable
Frontend: Click "Approve & Resume"
Backend: POST /api/protocols/{id}/approve → Saves edited draft
Backend: GET /api/protocols/{id}/stream/resume → Resumes supervisor
Supervisor: Finalizes protocol
Frontend: Status changes to "COMPLETED"
```

---

## ✅ Verification Checklist

- [x] Backend running on http://localhost:8000
- [x] Frontend running on http://localhost:5174
- [x] Agents defined in `backend/app/core/graph.py`
- [x] Graph topology configured with all 4 agents
- [x] SQLite checkpointing enabled
- [x] API endpoints implemented
- [x] SSE streaming configured
- [x] Frontend displays real-time agent activity
- [x] Blackboard state updates visible
- [x] Human-in-the-loop halt working
- [x] Draft approval and resume working

---

## 🎯 Summary

**Agents are working at these locations:**

1. **Drafting Agent** - `graph.py:83-132` - Generates CBT protocol drafts
2. **Safety Guardian** - `graph.py:135-178` - Scores safety (0.0-1.0)
3. **Clinical Critic** - `graph.py:181-221` - Scores empathy (0.0-1.0)
4. **Supervisor Agent** - `graph.py:224-314` - Routes and halts for human

**You can see agents working:**
- Real-time in Agent Activity panel
- State updates in Blackboard panel
- Draft generation in Draft panel
- Version history in Version History panel

**Complete workflow:**
1. Create session → 2. Start agents → 3. Watch execution → 4. Approve draft → 5. Get final protocol

**All agents are fully functional and production-ready!**
