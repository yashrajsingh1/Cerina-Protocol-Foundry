# Cerina Protocol Foundry - Startup Guide

## 🚀 Getting Started

### Step 1: Launch the System

#### Option A: One-Click Launch (Easiest)
```
Double-click: start_cerina.bat
```
This will automatically:
- Start the backend server (http://localhost:8000)
- Start the frontend dashboard (http://localhost:5174)
- Open the dashboard in your browser

#### Option B: Manual Launch

**Terminal 1 - Start Backend:**
```powershell
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload
```
Wait for: `Application startup complete`

**Terminal 2 - Start Frontend:**
```powershell
cd frontend
npm run dev
```
Wait for: `Local: http://localhost:5174`

**Open Dashboard:**
```
http://localhost:5174
```

---

## 📖 Dashboard Overview

The dashboard has 4 main sections:

### 1. **Left Sidebar - Session Management**
- **New Intent**: Text area to enter your CBT protocol request
- **Create Session**: Button to create a new session
- **Sessions List**: Shows all created sessions

### 2. **Top Header - Controls**
- **Start Agents**: Begins the autonomous agent execution
- **Waiting...**: Shows when system is processing

### 3. **Main Content Area - 4 Panels**

#### Panel 1: Blackboard State
- Shows real-time state of the system
- Displays: Iteration count, Safety score, Empathy score
- Updates as agents work

#### Panel 2: Draft (Human-in-the-Loop)
- Shows the current CBT protocol draft
- Editable when system halts for human review
- Status indicator: "Idle" or "Awaiting Approval"

#### Panel 3: Agent Activity
- Real-time log of agent actions
- Shows which agent is working and what they're doing
- Auto-scrolls to latest activity

#### Panel 4: Version History
- Tracks all draft iterations
- Shows scores for each version
- Expandable to view full content

---

## 🎯 How to Use - Step by Step

### Step 1: Create an Intent

1. Look at the **left sidebar**
2. Click in the **"New Intent"** text area
3. Type your CBT protocol request

**Example intents:**
- "Create an exposure hierarchy for agoraphobia"
- "Design a sleep hygiene protocol"
- "Build a social anxiety exposure exercise"
- "Create a procrastination management protocol"

### Step 2: Create Session

1. Click the **"Create Session"** button (green button)
2. Wait for the session to appear in the **Sessions List** below
3. Click on the session to select it

**What happens:**
- A new session is created in the database
- The blackboard is initialized
- The system is ready to start agents

### Step 3: Start Agents

1. Make sure your session is selected (highlighted in the list)
2. Click the **"Start Agents"** button (green button at top)
3. Watch the **Agent Activity** panel on the right

**What you'll see:**
```
Drafting Agent starts
  ↓
Creates initial CBT protocol draft
  ↓
Safety Guardian begins review
  ↓
Scores safety (0.0-1.0)
  ↓
Clinical Critic evaluates
  ↓
Scores empathy (0.0-1.0)
  ↓
Supervisor makes decision
  ↓
System halts for human review
```

### Step 4: Monitor Real-Time Updates

**Blackboard State Panel:**
- Watch `Iteration` count increase
- Watch `Safety` score update (0.0-1.0)
- Watch `Empathy` score update (0.0-1.0)

**Agent Activity Panel:**
- See each agent's actions in real-time
- Timestamps show when each action occurred
- Scroll to see all activity

**Draft Panel:**
- Updates as agents work
- Shows the current protocol being refined

### Step 5: Human Review & Approval

When the system halts (you'll see "⚠️ Awaiting Approval"):

1. **Review the Draft**
   - Read the generated CBT protocol
   - Check if it meets your needs

2. **Edit (Optional)**
   - Click in the draft text area
   - Make any changes you want
   - Fix tone, wording, or structure

3. **Approve & Resume**
   - Click the **"Approve & Resume"** button (blue button)
   - System resumes from where it halted
   - Supervisor finalizes the protocol

### Step 6: View Final Results

**After approval:**
- Status changes to "COMPLETED"
- **Version History** shows all iterations
- **Final Protocol** is saved to database

---

## 🔄 Agent Execution Flow

```
User Intent
    ↓
Create Session
    ↓
Initialize Blackboard
    ↓
Save to Database
    ↓
START AGENTS
    ↓
┌─────────────────────────────────┐
│ ITERATION LOOP                  │
├─────────────────────────────────┤
│ 1. Drafting Agent               │
│    - Creates/refines draft      │
│    - Incorporates feedback      │
│                                 │
│ 2. Safety Guardian              │
│    - Scores safety (0.0-1.0)    │
│    - Checks for harmful content │
│                                 │
│ 3. Clinical Critic              │
│    - Scores empathy (0.0-1.0)   │
│    - Evaluates quality          │
│                                 │
│ 4. Supervisor                   │
│    - Evaluates scores           │
│    - Decision:                  │
│      ├─ Loop again? (if scores  │
│      │  < 0.8 & iter < 3)       │
│      └─ Halt for human? (else)  │
└─────────────────────────────────┘
    ↓
MANDATORY HUMAN REVIEW
    ↓
User Reviews Draft
    ↓
User Edits (optional)
    ↓
User Approves
    ↓
Supervisor Finalizes
    ↓
Final Protocol Saved
```

---

## 📊 Understanding the Metrics

### Iteration Count
- Starts at 0
- Increments each time agents loop
- Max iterations: 3
- Shows how many refinement cycles occurred

### Safety Score (0.0-1.0)
- **1.0** = Fully safe, no harmful content
- **0.8+** = Acceptable safety level
- **<0.8** = Needs revision
- Checks for: self-harm, crisis guidance, medical claims

### Empathy Score (0.0-1.0)
- **1.0** = Maximally empathic and supportive
- **0.8+** = Good clinical quality
- **<0.8** = Needs improvement
- Evaluates: tone, clarity, helpfulness, structure

---

## 🎨 Dashboard Sections Explained

### Blackboard State
```
{
  "intent": "Create an exposure hierarchy for agoraphobia",
  "current_draft": "CBT Protocol for Agoraphobia...",
  "draft_versions": [...],
  "safety_score": 0.92,
  "empathy_score": 0.88,
  "iteration": 1,
  "notes": ["[DraftingAgent] Produced/updated draft.", ...]
}
```

### Agent Activity Log
Shows timeline of events:
```
drafting - start (Iteration 0)
drafting - finish (draft_preview: "CBT Protocol...")
safety_guardian - start
safety_guardian - finish (safety_score: 0.92)
clinical_critic - start
clinical_critic - finish (empathy_score: 0.88)
supervisor - start
supervisor - interrupt_for_human
```

### Version History
Each version shows:
- Version number (v0, v1, v2...)
- Safety score for that version
- Empathy score for that version
- Full content (expandable)

---

## ✅ Typical Workflow Example

### Example: "Create an exposure hierarchy for agoraphobia"

**1. Create Intent**
```
Type: "Create an exposure hierarchy for agoraphobia"
Click: "Create Session"
```

**2. Start Agents**
```
Click: "Start Agents"
Watch: Agent Activity panel
```

**3. First Iteration**
```
Drafting Agent: Creates initial exposure hierarchy
Safety Guardian: Scores 0.85 (good)
Clinical Critic: Scores 0.80 (acceptable)
Supervisor: Decides to loop (scores < 0.8 or < 3 iterations)
```

**4. Second Iteration**
```
Drafting Agent: Refines based on feedback
Safety Guardian: Scores 0.92 (excellent)
Clinical Critic: Scores 0.88 (excellent)
Supervisor: Halts for human review
```

**5. Human Review**
```
Status: "⚠️ Awaiting Approval"
You review the draft
You make minor edits (optional)
Click: "Approve & Resume"
```

**6. Finalization**
```
Supervisor: Finalizes protocol
Status: "COMPLETED"
Final protocol saved to database
Version history shows all iterations
```

---

## 🔧 Troubleshooting

### "No session selected" Message
- **Solution**: Create a session first, then click on it in the list

### "No events yet" in Agent Activity
- **Solution**: Click "Start Agents" to begin execution

### "No state yet" in Blackboard State
- **Solution**: Wait for agents to start, or click "Start Agents"

### Draft Text Not Updating
- **Solution**: Refresh the page or wait for agents to complete iteration

### Backend Not Responding
- **Solution**: 
  1. Check Terminal 1 for errors
  2. Ensure `uvicorn` is running
  3. Restart backend: `uvicorn app.main:app --reload`

### Frontend Not Loading
- **Solution**:
  1. Check Terminal 2 for errors
  2. Ensure `npm run dev` is running
  3. Try `http://localhost:5174` in browser

---

## 📝 Tips & Best Practices

### Writing Good Intents
- Be specific: "Create an exposure hierarchy for agoraphobia"
- Not vague: "Create a CBT protocol"
- Include context: "Design a sleep hygiene protocol for insomnia"

### Editing Drafts
- Only edit when system halts (⚠️ Awaiting Approval)
- Make clinical improvements, not structural changes
- Keep the CBT framework intact

### Monitoring Progress
- Watch Iteration count to see refinement cycles
- Check Safety/Empathy scores to understand quality
- Review Agent Activity to see what each agent did

### Version Comparison
- Expand version history to see all iterations
- Compare scores across versions
- See how agents improved the protocol

---

## 🎯 What Happens Behind the Scenes

### Session Creation
1. User enters intent
2. System creates unique session ID
3. Blackboard state initialized
4. Session saved to SQLite database

### Agent Execution
1. Drafting Agent generates/refines draft
2. Safety Guardian scores safety
3. Clinical Critic scores empathy
4. Supervisor decides: loop or halt
5. All state checkpointed to SQLite

### Human-in-the-Loop
1. Supervisor halts execution
2. Frontend shows "Awaiting Approval"
3. User reviews and edits draft
4. User clicks "Approve & Resume"
5. System resumes from checkpoint

### Finalization
1. Supervisor finalizes protocol
2. Final protocol saved to database
3. Session status = "COMPLETED"
4. Version history complete

---

## 🚀 Ready to Start!

You now have everything you need to:
1. ✅ Launch the system
2. ✅ Create sessions with intents
3. ✅ Watch autonomous agents work
4. ✅ Review and approve drafts
5. ✅ Get production-ready CBT protocols

**Start with the one-click launcher:**
```
Double-click: start_cerina.bat
```

**Then follow the workflow above!**

---

**Questions? Check the README.md for technical details or ARCHITECTURE.md for system design.**
