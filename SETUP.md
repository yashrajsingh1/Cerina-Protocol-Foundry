# Cerina Protocol Foundry – Setup & Run Guide

## Overview

**Cerina Protocol Foundry** is a production-ready, multi-agent autonomous CBT (Cognitive Behavioral Therapy) exercise generator with:

- **Backend**: Python + FastAPI + LangGraph with persistent SQLite checkpointing
- **Frontend**: React TypeScript dashboard with real-time streaming and human-in-the-loop refinement
- **MCP Integration**: Model Context Protocol server for machine-to-machine integration
- **Architecture**: Non-linear, self-correcting multi-agent system (Drafting Agent, Safety Guardian, Clinical Critic, Supervisor)

---

## Quick Start (One-Click)

### Windows

1. Open Windows Explorer and navigate to the project root folder.
2. **Double-click** `start_cerina.bat`.
3. Wait ~7 seconds; the dashboard opens automatically at `http://localhost:5173/`.

That's it! Both backend (port 8000) and frontend (port 5173) are now running.

---

## Manual Setup (First Time Only)

If you prefer to set up manually or the batch file doesn't work:

### 1. Backend Setup

```powershell
cd backend
python -m venv .venv
. .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
alembic upgrade head
```

### 2. Frontend Setup

```powershell
cd frontend
npm install
```

### 3. Run Backend

```powershell
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Run Frontend (in a new terminal)

```powershell
cd frontend
npm run dev
```

Then open: `http://localhost:5173/`

---

## Project Structure

```
cerina-protocol-foundry/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py          # Settings & environment variables
│   │   │   ├── db.py              # SQLAlchemy async engine & session
│   │   │   ├── graph.py           # LangGraph multi-agent workflow
│   │   │   └── llm.py             # LLM integration (Anthropic)
│   │   ├── api/
│   │   │   ├── deps.py            # FastAPI dependency injection
│   │   │   └── protocols.py       # REST endpoints & SSE streaming
│   │   ├── models/
│   │   │   └── session.py         # SQLAlchemy ORM models
│   │   ├── schemas/
│   │   │   └── protocols.py       # Pydantic request/response schemas
│   │   └── main.py                # FastAPI app setup
│   ├── mcp_server/
│   │   └── server.py              # MCP (Model Context Protocol) server
│   ├── alembic/                   # Database migrations
│   ├── requirements.txt           # Python dependencies
│   └── alembic.ini                # Alembic configuration
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # Main React dashboard component
│   │   ├── api.ts                 # TypeScript API client
│   │   └── main.tsx               # React entry point
│   ├── index.html                 # HTML template
│   ├── package.json               # Node dependencies
│   ├── tsconfig.json              # TypeScript configuration
│   └── vite.config.ts             # Vite build configuration
├── start_cerina.bat               # One-click launcher (Windows)
├── README.md                       # Full documentation
├── SETUP.md                        # This file
└── .gitignore                      # Git ignore rules
```

---

## Frontend UI Overview

When you open `http://localhost:5173/`, you'll see:

### Top Section
- **Intent Input**: Text area to describe your CBT exercise goal (e.g., "Create an exposure hierarchy for agoraphobia")
- **Create Session**: Button to start a new protocol generation session
- **Session Selector**: Dropdown showing all sessions with status badges (`PENDING`, `RUNNING`, `AWAITING_HUMAN`, `COMPLETED`)
- **Action Buttons**: "Start Agents" and "Refresh State"

### Left Panel – Session & Agent Activity
- **Session Details**: ID, creation time, status, original intent
- **Agent Activity Feed**: Real-time streaming log of agent actions:
  - `DraftingAgent`: Creates and revises the CBT draft
  - `SafetyGuardian`: Checks for safety issues
  - `ClinicalCritic`: Evaluates empathy and structure
  - `Supervisor`: Routes tasks and decides when to halt for human

### Middle Panel – Blackboard & Version History
- **Blackboard Snapshot**: Current state metrics (iteration count, safety score, empathy score, routing decision)
- **Version History**: List of draft versions with previews; click to inspect previous iterations

### Right Panel – Human-in-the-Loop Editor
- **Draft Editor**: When the graph halts, the current draft appears in an editable text area
- **Status**: Shows `AWAITING_HUMAN` when paused
- **Approve & Resume**: Button to send your edited draft back to the backend and finalize the protocol
- **Final Protocol**: After completion, displays the final CBT exercise

---

## Workflow Example

1. **Create Session**
   - Enter intent: "Create a sleep hygiene protocol for insomnia"
   - Click "Create Session"
   - Session appears in dropdown as `PENDING`

2. **Start Agents**
   - Select the session
   - Click "Start Agents"
   - Watch the agent activity feed in real-time
   - Blackboard metrics update as agents work

3. **Human Review & Edit**
   - Graph halts automatically (status: `AWAITING_HUMAN`)
   - Current draft appears in the right panel's text editor
   - You can edit, refine, or approve as-is

4. **Finalize**
   - Click "Approve & Resume"
   - Backend resumes LangGraph execution
   - Supervisor finalizes and saves the protocol
   - Status becomes `COMPLETED`
   - Final protocol and full history are stored in the database

---

## Environment Variables

Create a `.env` file in the `backend/` folder if you need to customize settings:

```env
CERINA_APP_DB_URL=sqlite+aiosqlite:///./cerina_app.db
CERINA_CHECKPOINT_DB_PATH=cerina_checkpoints.db
ANTHROPIC_API_KEY=your_api_key_here
CERINA_MODEL_NAME=claude-3-5-sonnet-20240620
CERINA_FRONTEND_ORIGIN=http://localhost:5173
```

If `ANTHROPIC_API_KEY` is not set, the system uses a stubbed LLM response for development.

---

## MCP Server (Machine-to-Machine Integration)

To use the MCP server with Claude Desktop or another MCP client:

```powershell
cd backend
. .venv\Scripts\activate
python -m mcp_server.server
```

Then configure your MCP client to connect to this server. You can then ask Claude:

> "Ask Cerina Foundry to create a sleep hygiene protocol."

This triggers the same LangGraph workflow and returns the final CBT protocol.

---

## Troubleshooting

### Port Already in Use
If port 8000 or 5173 is already in use:
- Change the port in `start_cerina.bat` or manually specify: `uvicorn app.main:app --port 8001`

### Database Locked
If you see SQLite lock errors:
- Close all running instances of the app
- Delete `cerina_app.db` and `cerina_checkpoints.db` to start fresh
- Re-run the backend

### Frontend Not Connecting
- Ensure backend is running on `http://localhost:8000`
- Check browser console (F12) for CORS or network errors
- Verify `CERINA_FRONTEND_ORIGIN` in backend config matches your frontend URL

### Missing Dependencies
```powershell
cd backend
. .venv\Scripts\activate
python -m pip install -r requirements.txt --upgrade
```

---

## Production Deployment

For production:

1. **Use a real database**: Replace SQLite with PostgreSQL
2. **Set environment variables**: Use a secrets manager for `ANTHROPIC_API_KEY`
3. **Run migrations**: `alembic upgrade head`
4. **Use a production ASGI server**: `gunicorn` or `hypercorn` instead of `uvicorn --reload`
5. **Build frontend**: `npm run build` and serve via a CDN or static server
6. **Enable HTTPS**: Use a reverse proxy (nginx, Caddy) with SSL certificates

---

## Support & Documentation

- **Full Architecture**: See `README.md`
- **API Endpoints**: See `backend/app/api/protocols.py`
- **LangGraph Workflow**: See `backend/app/core/graph.py`
- **Frontend Components**: See `frontend/src/App.tsx`

---

## License

This project is part of the Cerina Protocol Foundry initiative.

---

**Ready to deliver!** Double-click `start_cerina.bat` and start building CBT protocols.
