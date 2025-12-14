# Cerina Protocol Foundry – Project Index

## 📋 Quick Navigation

### Getting Started
- **[SETUP.md](SETUP.md)** – Installation, one-click launcher, and troubleshooting
- **[ARCHITECTURE.md](ARCHITECTURE.md)** – System design, agent topology, data flow
- **[README.md](README.md)** – Full documentation with API reference

### Project Structure
```
cerina-protocol-foundry/
├── 📄 start_cerina.bat              ← Double-click to launch everything
├── 📄 SETUP.md                      ← Setup & run instructions
├── 📄 ARCHITECTURE.md               ← System design & topology
├── 📄 README.md                     ← Full documentation
├── 📄 INDEX.md                      ← This file
├── 📄 .gitignore                    ← Git ignore rules
│
├── backend/                         ← Python FastAPI + LangGraph
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py            ← Settings & environment
│   │   │   ├── db.py                ← SQLAlchemy setup
│   │   │   ├── graph.py             ← LangGraph workflow (core logic)
│   │   │   └── llm.py               ← LLM integration
│   │   ├── api/
│   │   │   ├── deps.py              ← FastAPI dependencies
│   │   │   └── protocols.py         ← REST endpoints & SSE
│   │   ├── models/
│   │   │   └── session.py           ← Database models
│   │   ├── schemas/
│   │   │   └── protocols.py         ← Pydantic schemas
│   │   └── main.py                  ← FastAPI app
│   ├── mcp_server/
│   │   └── server.py                ← MCP integration
│   ├── alembic/                     ← Database migrations
│   ├── requirements.txt             ← Python dependencies
│   ├── alembic.ini                  ← Alembic config
│   └── .venv/                       ← Virtual environment (auto-created)
│
├── frontend/                        ← React TypeScript + Vite
│   ├── src/
│   │   ├── App.tsx                  ← Main dashboard component
│   │   ├── api.ts                   ← TypeScript API client
│   │   └── main.tsx                 ← React entry point
│   ├── index.html                   ← HTML template
│   ├── package.json                 ← Node dependencies
│   ├── tsconfig.json                ← TypeScript config
│   ├── vite.config.ts               ← Vite config
│   └── node_modules/                ← Dependencies (auto-created)
│
└── .gitignore                       ← Git ignore rules
```

---

## 🚀 Quick Start

### Windows (One-Click)
```powershell
# Double-click start_cerina.bat in Windows Explorer
# Or run in PowerShell:
.\start_cerina.bat
```

### Manual (First Time Setup)
```powershell
# Backend
cd backend
python -m venv .venv
. .venv\Scripts\activate
python -m pip install -r requirements.txt
alembic upgrade head

# Frontend (in new terminal)
cd frontend
npm install

# Run Backend
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run Frontend (in new terminal)
cd frontend
npm run dev
```

Then open: **http://localhost:5173/**

---

## 🏗️ Architecture at a Glance

### Multi-Agent System
```
User Intent
    ↓
[Drafting Agent] → Creates initial draft
    ↓
[Safety Guardian] → Checks for unsafe content
    ↓
[Clinical Critic] → Evaluates empathy & structure
    ↓
[Supervisor] → Routes (loop or halt for human)
    ↓
[Human-in-the-Loop] → User edits & approves
    ↓
Final CBT Protocol (saved to DB)
```

### Key Features
- ✅ **Non-linear**: Agents can loop autonomously before human involvement
- ✅ **Self-correcting**: Supervisor makes routing decisions based on scores
- ✅ **Persistent**: SQLite checkpointing for crash recovery
- ✅ **Real-time**: SSE streaming of agent activity to React dashboard
- ✅ **Human-in-the-loop**: Mandatory approval before finalization
- ✅ **MCP Integration**: Reuses same workflow for machine-to-machine use

---

## 📊 Frontend UI Sections

### Top Bar
- Intent input field
- Create Session button
- Session selector dropdown
- Start Agents & Refresh buttons

### Left Panel
- Session details (ID, status, created time)
- Real-time agent activity feed (streaming)

### Middle Panel
- Blackboard snapshot (metrics, scores, routing decision)
- Version history (draft v1, v2, v3…)

### Right Panel
- **When Running**: Blackboard visualization
- **When Halted**: Editable draft text area + "Approve & Resume" button
- **When Complete**: Final protocol display + history

---

## 🔌 API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/protocols` | Create new session |
| GET | `/api/protocols` | List all sessions |
| GET | `/api/protocols/{id}` | Get session details |
| GET | `/api/protocols/{id}/blackboard` | Get blackboard state |
| POST | `/api/protocols/{id}/stream/start` | Start workflow (SSE) |
| POST | `/api/protocols/{id}/approve` | Save human edits |
| POST | `/api/protocols/{id}/stream/resume` | Resume after approval (SSE) |

---

## 🤖 MCP Integration

Run the MCP server:
```powershell
cd backend
. .venv\Scripts\activate
python -m mcp_server.server
```

Then in Claude Desktop or another MCP client, ask:
> "Ask Cerina Foundry to create a sleep hygiene protocol."

The server reuses the same LangGraph workflow and returns the final protocol.

---

## 📦 Technology Stack

### Backend
- **Framework**: FastAPI 0.115.12
- **Agent Orchestration**: LangGraph 1.0.4
- **Database**: SQLite + SQLAlchemy 2.0.36
- **Checkpointing**: langgraph-checkpoint-sqlite 3.0.1
- **LLM**: Anthropic Claude (via langchain-core)
- **MCP**: mcp 1.6.0, fastmcp 2.0.0
- **Async**: aiosqlite 0.20.0, uvicorn 0.30.6

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: CSS (inline)
- **HTTP Client**: Fetch API + EventSource (SSE)

### Database
- **App DB**: SQLite (cerina_app.db)
- **Checkpoints**: SQLite (cerina_checkpoints.db)
- **Migrations**: Alembic 1.13.3

---

## 🧪 Testing the System

### 1. Create a Session
- Intent: "Create an exposure hierarchy for agoraphobia"
- Click "Create Session"

### 2. Start Agents
- Select session
- Click "Start Agents"
- Watch agent activity stream in real-time

### 3. Review & Edit
- When halted, edit the draft in the right panel
- Click "Approve & Resume"

### 4. Verify Results
- Check final protocol
- Review version history
- Inspect agent logs

---

## 🔧 Environment Variables

Create `.env` in `backend/` folder:
```env
CERINA_APP_DB_URL=sqlite+aiosqlite:///./cerina_app.db
CERINA_CHECKPOINT_DB_PATH=cerina_checkpoints.db
ANTHROPIC_API_KEY=your_key_here
CERINA_MODEL_NAME=claude-3-5-sonnet-20240620
CERINA_FRONTEND_ORIGIN=http://localhost:5173
```

If `ANTHROPIC_API_KEY` is not set, the system uses a stubbed LLM for development.

---

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| **INDEX.md** | This file – quick navigation |
| **SETUP.md** | Installation & run instructions |
| **ARCHITECTURE.md** | System design, topology, data flow |
| **README.md** | Full documentation with detailed API reference |

---

## ✅ Checklist for Submission

- [x] Backend: FastAPI + LangGraph multi-agent system
- [x] Frontend: React TypeScript dashboard with HITL
- [x] Database: SQLite with persistent checkpointing
- [x] MCP: Server reusing LangGraph workflow
- [x] Documentation: SETUP.md, ARCHITECTURE.md, README.md
- [x] One-click launcher: start_cerina.bat
- [x] Clean folder structure (no unnecessary files)
- [x] Production-ready code
- [x] Real-time streaming (SSE)
- [x] Human-in-the-loop approval flow

---

## 🎯 Next Steps

1. **Double-click `start_cerina.bat`** to launch everything
2. **Open `http://localhost:5173/`** in your browser
3. **Create a session** with your intent
4. **Click "Start Agents"** and watch the magic happen
5. **Edit & approve** the draft when halted
6. **Review the final protocol** and history

---

## 📞 Support

If you encounter issues:
1. Check **SETUP.md** troubleshooting section
2. Review **ARCHITECTURE.md** for system design details
3. Check browser console (F12) for frontend errors
4. Check backend terminal for Python errors

---

## 📄 License

Cerina Protocol Foundry – Ready for delivery and evaluation.

---

**Built with ❤️ using FastAPI, LangGraph, React, and TypeScript.**
