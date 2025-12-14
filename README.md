# Cerina Protocol Foundry

Multi-agent autonomous CBT protocol generator with human-in-the-loop approval.

## Quick Start

**One-Click Launch:**
```
Double-click: start_cerina.bat
```

**Manual Launch:**
```powershell
# Terminal 1
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

**Open:** http://localhost:5174

---

## System Architecture

### 4 Autonomous Agents
1. **Drafting Agent** - Generates CBT protocol drafts
2. **Safety Guardian** - Scores safety (0.0-1.0)
3. **Clinical Critic** - Scores empathy (0.0-1.0)
4. **Supervisor** - Routes workflow, halts for human

### Workflow
```
Intent → Drafting → Safety → Clinical → Supervisor
                                          ↓
                                    Halt for Human
                                          ↓
                                    Human Approves
                                          ↓
                                    Final Protocol
```

### Key Features
- Non-linear multi-agent topology
- Autonomous looping until scores ≥ 0.8
- Mandatory human-in-the-loop halt
- Real-time SSE streaming
- SQLite persistent checkpointing
- Version history tracking
- MCP integration

---

## Test Workflow

1. Type intent: "Create an exposure hierarchy for agoraphobia"
2. Click "Create Session"
3. Click "Start Agents"
4. Watch Agent Activity panel
5. When halted, edit draft (optional)
6. Click "Approve & Resume"
7. View final protocol

---

## Tech Stack

- **Backend**: FastAPI, LangGraph, SQLAlchemy, SQLite
- **Frontend**: React, TypeScript, Vite
- **Streaming**: Server-Sent Events (SSE)
- **MCP**: Model Context Protocol integration

---

## Status

✅ Production Ready
