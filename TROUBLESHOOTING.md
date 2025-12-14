# Cerina Protocol Foundry - Troubleshooting Guide

## Issue: "Create Session" Button Not Working

### Symptoms
- Button appears clickable but nothing happens
- No error message displayed
- Sessions list remains empty

### Quick Fixes (Try These First)

#### 1. Check Backend is Running
Open a new terminal and run:
```powershell
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok"}
```

If you get "connection refused":
- **Backend is NOT running**
- Go to Terminal 1 where backend should be running
- Check for errors
- Restart: `uvicorn app.main:app --reload`

#### 2. Check Frontend is Running
Open browser console (F12) and check for errors:
- Red errors in console
- Network tab shows failed requests
- Check Terminal 2 for `npm run dev` errors

#### 3. Check Browser Console (F12)
Look for error messages:
- "Failed to create session"
- "Network error"
- "CORS error"

#### 4. Clear Browser Cache
```
Ctrl+Shift+Delete (or Cmd+Shift+Delete on Mac)
Clear all data
Refresh page
```

#### 5. Restart Everything
```powershell
# Terminal 1 - Kill backend
Ctrl+C

# Terminal 2 - Kill frontend
Ctrl+C

# Restart backend
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload

# Restart frontend (new terminal)
cd frontend
npm run dev
```

---

## Common Issues & Solutions

### Issue 1: "Please enter an intent" Alert
**Problem**: Button shows alert even though text is entered

**Solution**:
1. Make sure text is in the textarea
2. Check that text has no leading/trailing spaces
3. Try typing a simple test: "test"
4. Click button again

### Issue 2: "Error creating session: Failed to create session"
**Problem**: Backend rejects the request

**Causes & Solutions**:

**A. Database not initialized**
```powershell
cd backend
. .venv\Scripts\activate
alembic upgrade head
```

**B. Database file corrupted**
```powershell
# Delete old database
rm cerina_app.db
rm cerina_checkpoints.db

# Restart backend (will recreate)
uvicorn app.main:app --reload
```

**C. Port 8000 already in use**
```powershell
# Check what's using port 8000
netstat -ano | Select-String ":8000"

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or use different port
uvicorn app.main:app --port 8001 --reload
```

### Issue 3: CORS Error
**Problem**: Browser console shows CORS error

**Solution**:
1. Check backend is running on `http://localhost:8000`
2. Check frontend is running on `http://localhost:5173` or `http://localhost:5174`
3. Verify CORS is configured in `backend/app/main.py`
4. Restart both servers

### Issue 4: Sessions List Shows "No sessions yet"
**Problem**: Sessions created but not appearing in list

**Solution**:
1. Refresh page (F5)
2. Check browser console for errors
3. Verify backend database has data:
```powershell
# Check if database file exists
ls cerina_app.db
```

---

## Detailed Debugging Steps

### Step 1: Check Backend Health
```powershell
# Terminal 1
curl http://localhost:8000/health
```

Expected:
```json
{"status": "ok"}
```

### Step 2: Check API Endpoint Directly
```powershell
# Create a test session via curl
$body = @{ intent = "Test intent" } | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8000/api/protocols" `
  -Method POST `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

Expected response: Session object with id, intent, status, etc.

### Step 3: Check Browser Network Tab
1. Open F12 (Developer Tools)
2. Go to Network tab
3. Click "Create Session"
4. Look for POST request to `/api/protocols`
5. Check:
   - Status code (should be 200)
   - Response body (should have session data)
   - Request headers (should have Content-Type: application/json)

### Step 4: Check Backend Logs
Look at Terminal 1 where backend is running:
- Should show: `POST /api/protocols`
- Should show status code
- Should show any errors

### Step 5: Check Database
```powershell
# Install sqlite3 if needed
# Then check database
sqlite3 cerina_app.db "SELECT * FROM protocol_sessions;"
```

---

## Advanced Troubleshooting

### Enable Debug Logging

**Backend:**
Edit `backend/app/core/db.py`:
```python
engine = create_async_engine(
    settings.app_db_url, 
    echo=True,  # Add this line
    future=True
)
```

**Frontend:**
Already has console.log statements. Check F12 console.

### Check Environment Variables
```powershell
# Verify settings
$env:CERINA_APP_DB_URL
$env:CERINA_CHECKPOINT_DB_PATH
$env:CERINA_FRONTEND_ORIGIN
```

### Verify Dependencies
```powershell
# Backend
cd backend
. .venv\Scripts\activate
pip list | grep -E "fastapi|sqlalchemy|langgraph"

# Frontend
cd frontend
npm list react react-dom
```

---

## If All Else Fails

### Nuclear Option: Complete Reset
```powershell
# 1. Kill all processes
Ctrl+C in both terminals

# 2. Delete all generated files
rm cerina_app.db
rm cerina_checkpoints.db
rm -r backend/.venv
rm -r frontend/node_modules

# 3. Reinstall everything
cd backend
python -m venv .venv
. .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head

cd ../frontend
npm install

# 4. Start fresh
# Terminal 1
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

---

## Getting Help

### Information to Provide
If you need help, provide:
1. Screenshot of the issue
2. Browser console errors (F12)
3. Backend terminal output
4. Steps you've already tried
5. Operating system (Windows/Mac/Linux)

### Check These Files
- `backend/app/api/protocols.py` - API endpoint
- `frontend/src/App.tsx` - Create Session handler
- `frontend/src/api.ts` - API client
- `backend/app/main.py` - FastAPI setup

---

## Success Indicators

✅ **Backend Running**
```
INFO:     Application startup complete.
```

✅ **Frontend Running**
```
Local:   http://localhost:5173
```

✅ **Session Created**
- Alert: "Session created successfully!"
- Session appears in Sessions list
- Can click on session to select it

✅ **Ready to Start Agents**
- Session is selected (highlighted)
- "Start Agents" button is enabled
- Click "Start Agents" to begin

---

## Next Steps

Once "Create Session" works:
1. ✅ Create a session with an intent
2. Click on the session to select it
3. Click "Start Agents"
4. Watch Agent Activity panel
5. When halted, review and approve draft

**You're now ready to use Cerina Protocol Foundry!**
