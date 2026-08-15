# PayCrew API — ngrok public URL for Shresth

## 1. Install ngrok
Download: https://ngrok.com/download  
Or: `winget install ngrok.ngrok`

## 2. Auth (one time)
```powershell
ngrok config add-authtoken YOUR_NGROK_TOKEN
```

## 3. Start backend + ngrok
```powershell
cd d:\Hackathons\AgentForge\backend
.\scripts\start_ngrok.ps1
```

Or manually in two terminals:
```powershell
# Terminal 1
.\.venv\Scripts\uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2
ngrok http 8000
```

## 4. Send Shresth the ngrok URL

From ngrok output, copy `https://xxxx.ngrok-free.app`

**Base URL:** `https://xxxx.ngrok-free.app/v1`  
**Swagger:** `https://xxxx.ngrok-free.app/docs`  
**WebSocket:** `wss://xxxx.ngrok-free.app/v1/ws?token=TOKEN`

## Auth codes for testing
- AP: `AP2024`
- CFO: `CFO2024`

## Login
```
POST /v1/auth/login
{ "code": "AP2024" }
→ { "token": "...", "role": "ap" }
```

Use `Authorization: Bearer <token>` on all AP/CFO routes.
