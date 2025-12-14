# 🚀 Cerina Protocol Foundry – Quick Start

## One-Click Launch

### Windows
Double-click: `start_cerina.bat`

That's it! Backend + Frontend will start automatically and open the dashboard.

---

## Manual Launch

### Terminal 1 – Backend
```powershell
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 – Frontend
```powershell
cd frontend
npm run dev
```

### Open Dashboard
```
http://localhost:5174/
```

---

## How to Use

1. **Create Intent**: Type your intent in the sidebar (e.g., "Create an exposure hierarchy for agoraphobia")
2. **Create Session**: Click "Create Session"
3. **Start Agents**: Click "Start Agents" button
4. **Watch Real-Time**: See agents working in the activity log
5. **Edit Draft**: When halted, edit the draft in the editor
6. **Approve**: Click "Approve & Resume" to finalize

---

## What You'll See

- **Left Sidebar**: Session management and intent input
- **Top Header**: Selected session and control buttons
- **Left Panel**: Blackboard state and draft editor
- **Right Panel**: Agent activity log and version history

---

## Features

✅ Multi-agent autonomous system (Drafting, Safety, Clinical, Supervisor)  
✅ Real-time streaming of agent activity  
✅ Human-in-the-loop draft approval  
✅ Persistent SQLite checkpointing  
✅ Version history tracking  
✅ Production-ready UI  
✅ MCP integration for machine-to-machine use  

---

## Tech Stack

- **Backend**: FastAPI + LangGraph + SQLite
- **Frontend**: React + TypeScript + Vite
- **Database**: SQLite with persistent checkpointing
- **MCP**: Model Context Protocol integration

---

## Project Structure

```
cerina-protocol-foundry/
├── start_cerina.bat              ← One-click launcher
├── QUICK_START.md                ← This file
├── README.md                     ← Full documentation
├── SETUP.md                      ← Installation guide
├── ARCHITECTURE.md               ← System design
├── INDEX.md                      ← Navigation guide
├── START_HERE.md                 ← Getting started
│
├── backend/                      ← Python backend
│   ├── app/core/graph.py         ← LangGraph workflow
│   ├── app/api/protocols.py      ← REST endpoints
│   ├── app/models/session.py     ← Database models
│   ├── mcp_server/server.py      ← MCP server
│   └── requirements.txt          ← Dependencies
│
├── frontend/                     ← React frontend
│   ├── src/App.tsx               ← Main dashboard
│   ├── src/api.ts                ← API client
│   ├── package.json              ← Dependencies
│   └── vite.config.ts            ← Build config
│
└── .gitignore                    ← Git rules
```

---

## Troubleshooting

**Port already in use?**
- Change port in `start_cerina.bat` or run: `uvicorn app.main:app --port 8001`

**Database locked?**
- Delete `cerina_app.db` and `cerina_checkpoints.db`
- Restart the app

**Frontend not connecting?**
- Ensure backend is running on `http://localhost:8000`
- Check browser console (F12) for errors

**Missing dependencies?**
```powershell
cd backend
. .venv\Scripts\activate
pip install -r requirements.txt --upgrade
```

---

**Ready to go! Start the system and create your first protocol.** 🎉
