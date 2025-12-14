# Quick Fix - "Create Session" Button Not Working

## Immediate Solution

### Step 1: Open Browser Console
Press **F12** to open Developer Tools, then go to **Console** tab.

### Step 2: Try Creating Session Again
1. Type intent in the text area: "Design a sleep hygiene protocol"
2. Click "Create Session" button
3. **Look at the Console** for error messages

### Step 3: Check What Error You See

#### Error A: "Failed to create session: 500"
**Backend is having issues**
- Go to Terminal 1 (backend)
- Look for error messages
- Restart backend:
```powershell
Ctrl+C
uvicorn app.main:app --reload
```

#### Error B: "Failed to create session: connection refused"
**Backend is not running**
- Open Terminal 1
- Run:
```powershell
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload
```
- Wait for: `Application startup complete`

#### Error C: "Failed to create session: CORS error"
**Frontend/Backend communication issue**
- Restart both:
```powershell
# Terminal 1 - Backend
Ctrl+C
uvicorn app.main:app --reload

# Terminal 2 - Frontend
Ctrl+C
npm run dev
```

#### Error D: No error, but nothing happens
**Button click not registering**
- Refresh page: **F5**
- Try again
- If still nothing, check Terminal 2 (frontend) for errors

---

## Verify Backend is Running

Open a new Terminal and run:
```powershell
curl http://localhost:8000/health
```

**Should return:**
```json
{"status": "ok"}
```

If you get "connection refused", backend is NOT running.

---

## Verify Frontend is Running

Check Terminal 2 output. Should show:
```
Local:   http://localhost:5174
```

If not, run:
```powershell
cd frontend
npm run dev
```

---

## Complete Reset (If Nothing Works)

```powershell
# Kill both terminals
Ctrl+C in Terminal 1
Ctrl+C in Terminal 2

# Delete databases
rm cerina_app.db
rm cerina_checkpoints.db

# Restart backend
cd backend
. .venv\Scripts\activate
uvicorn app.main:app --reload

# Restart frontend (new terminal)
cd frontend
npm run dev

# Try again
```

---

## Success Indicators

✅ **Button works when:**
- You see alert: "Session created successfully!"
- Session appears in the Sessions list on left
- Can click on session to select it

✅ **Next step:**
- Click on the session to select it
- Click "Start Agents"
- Watch Agent Activity panel

---

## Still Not Working?

1. **Check F12 Console** - What error do you see?
2. **Check Terminal 1** - Any error messages?
3. **Check Terminal 2** - Any error messages?
4. **Try the Complete Reset** above
5. **Share the error message** from F12 Console

---

**Once "Create Session" works, you're ready to use the system!**
