# 🚀 Cerina Protocol Foundry – START HERE

## What You Have

A **production-ready, fully functional multi-agent autonomous CBT protocol generator** with:
- Non-linear, self-correcting agent architecture
- Real-time React dashboard with human-in-the-loop refinement
- Persistent SQLite checkpointing for crash recovery
- MCP integration for machine-to-machine use
- Complete documentation and one-click launcher

---

## ⚡ Quick Start (30 seconds)

### Windows Users
1. Open Windows Explorer
2. Navigate to: `c:\Users\yashraj\Desktop\New folder (6)\`
3. **Double-click** `start_cerina.bat`
4. Wait ~7 seconds; dashboard opens automatically at `http://localhost:5173/`

**That's it!** Both backend (port 8000) and frontend (port 5173) are now running.

---

## 📖 Documentation Map

| File | Read This For |
|------|---|
| **START_HERE.md** | Quick start (you are here) |
| **INDEX.md** | Project overview & navigation |
| **SETUP.md** | Installation, troubleshooting, environment variables |
| **ARCHITECTURE.md** | System design, agent topology, data flow |
| **README.md** | Full API reference, detailed documentation |
| **DELIVERY_SUMMARY.md** | What's included, checklist, evaluation guide |

---

## 🎯 What to Do Next

### 1. Launch the System
```powershell
# Windows: Double-click start_cerina.bat
# Or manually:
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal:
cd frontend
npm run dev
```

### 2. Open the Dashboard
```
http://localhost:5173/
```

### 3. Create Your First Protocol
1. **Enter Intent**: "Create an exposure hierarchy for agoraphobia"
2. **Click "Create Session"**
3. **Click "Start Agents"**
4. Watch agents work in real-time:
   - Drafting Agent creates the initial draft
   - Safety Guardian checks for safety issues
   - Clinical Critic evaluates empathy and structure
   - Supervisor decides: loop again or halt for human?
5. **When Halted**: Edit the draft in the right panel
6. **Click "Approve & Resume"**: Finalize and save

### 4. Explore the UI
- **Left Panel**: Session details + real-time agent activity log
- **Middle Panel**: Blackboard metrics + version history
- **Right Panel**: Draft editor + final protocol display

---

## 🏗️ System Architecture (30-Second Overview)

```
User Intent
    ↓
[Drafting Agent] → Creates draft
    ↓
[Safety Guardian] → Checks safety
    ↓
[Clinical Critic] → Evaluates quality
    ↓
[Supervisor] → Routes (loop or halt?)
    ↓
[Human-in-the-Loop] → User edits & approves
    ↓
Final CBT Protocol (saved to SQLite)
```

**Key Features**:
- ✅ Agents can loop autonomously before human involvement
- ✅ Shared blackboard state for inter-agent communication
- ✅ SQLite checkpointing for crash recovery
- ✅ Real-time SSE streaming to React dashboard
- ✅ Mandatory human approval before finalization

---

## 📁 Project Structure

```
cerina-protocol-foundry/
├── start_cerina.bat              ← ONE-CLICK LAUNCHER
├── START_HERE.md                 ← This file
├── INDEX.md, SETUP.md, ARCHITECTURE.md, README.md, DELIVERY_SUMMARY.md
├── backend/                      ← Python + FastAPI + LangGraph
│   ├── app/core/graph.py         ← Multi-agent workflow (267 lines)
│   ├── app/api/protocols.py      ← REST endpoints (318 lines)
│   ├── app/models/session.py     ← Database models (77 lines)
│   ├── mcp_server/server.py      ← MCP integration (133 lines)
│   └── requirements.txt          ← Python dependencies
├── frontend/                     ← React + TypeScript + Vite
│   ├── src/App.tsx               ← Dashboard component (710 lines)
│   ├── src/api.ts                ← API client
│   └── package.json              ← Node dependencies
└── .gitignore                    ← Git ignore rules
```

---

## 🔑 Key Files to Understand

### Backend Logic
- **`backend/app/core/graph.py`** – LangGraph workflow with 4 agents
- **`backend/app/api/protocols.py`** – REST API endpoints & SSE streaming
- **`backend/app/models/session.py`** – Database schema

### Frontend
- **`frontend/src/App.tsx`** – Main React dashboard
- **`frontend/src/api.ts`** – TypeScript API client

### MCP
- **`backend/mcp_server/server.py`** – MCP server (reuses LangGraph)

---

## 🧪 Testing the System

### Test 1: Create a Protocol
1. Enter intent: "Create a sleep hygiene protocol for insomnia"
2. Click "Create Session"
3. Click "Start Agents"
4. Watch streaming agent activity
5. Edit draft when halted
6. Click "Approve & Resume"
7. Verify final protocol is saved

### Test 2: View History
1. Select a completed session
2. Click "Refresh State"
3. Check version history (middle panel)
4. Click on previous versions to see draft evolution

### Test 3: MCP Integration (Optional)
```powershell
cd backend
. .venv\Scripts\activate
python -m mcp_server.server
```
Then in Claude Desktop: "Ask Cerina Foundry to create a sleep hygiene protocol."

---

## 🛠️ Troubleshooting

### Port Already in Use
- Change port in `start_cerina.bat` or run: `uvicorn app.main:app --port 8001`

### Database Locked
- Close all running instances
- Delete `cerina_app.db` and `cerina_checkpoints.db`
- Restart the app

### Frontend Not Connecting
- Ensure backend is running on `http://localhost:8000`
- Check browser console (F12) for errors
- Verify CORS origin in `backend/app/core/config.py`

### Missing Dependencies
```powershell
cd backend
. .venv\Scripts\activate
python -m pip install -r requirements.txt --upgrade
```

---

## 📊 Technology Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI 0.115.12 + LangGraph 1.0.4 |
| **Database** | SQLite + SQLAlchemy 2.0.36 |
| **Checkpointing** | langgraph-checkpoint-sqlite 3.0.1 |
| **Frontend** | React 18 + TypeScript + Vite |
| **MCP** | mcp 1.6.0 + fastmcp 2.0.0 |
| **LLM** | Anthropic Claude (via langchain-core) |

---

## ✅ What's Included

- ✅ **Backend**: FastAPI + LangGraph multi-agent system
- ✅ **Frontend**: React TypeScript dashboard with real-time streaming
- ✅ **Database**: SQLite with persistent checkpointing
- ✅ **MCP Server**: Reuses LangGraph workflow for machine-to-machine use
- ✅ **Documentation**: 5 comprehensive guides
- ✅ **One-Click Launcher**: `start_cerina.bat` for Windows
- ✅ **Production-Ready Code**: Modular, type-safe, well-documented
- ✅ **Human-in-the-Loop**: Mandatory approval before finalization
- ✅ **Real-Time Streaming**: SSE for live agent activity
- ✅ **Crash Recovery**: Checkpointing ensures no data loss

---

## 🎓 Architecture Highlights

### Non-Linear Agent Topology
- Supervisor can route back to drafting multiple times
- Autonomous self-correction before human involvement
- Reduces unnecessary human interruptions

### Deep Shared Blackboard State
- All agents read/write to single `BlackboardState` dict
- Rich inter-agent communication (notes, feedback)
- Tracks versions, scores, iteration count

### Persistent Checkpointing
- Every step checkpointed to SQLite
- On crash, graph resumes from last checkpoint
- No loss of work or state

### Human-in-the-Loop
- Graph halts before finalization (not after)
- Human can edit draft before it's locked in
- Ensures human approval is mandatory

---

## 📞 Need Help?

1. **Quick questions**: Check **SETUP.md** troubleshooting
2. **System design**: Read **ARCHITECTURE.md**
3. **API details**: See **README.md**
4. **What's included**: Review **DELIVERY_SUMMARY.md**

---

## 🚀 You're Ready!

Everything is set up and ready to go. Just:

1. **Double-click** `start_cerina.bat`
2. **Wait** for the dashboard to open
3. **Create a session** and start generating CBT protocols

**Enjoy!** 🎉

---

**Built with ❤️ using FastAPI, LangGraph, React, and TypeScript.**
