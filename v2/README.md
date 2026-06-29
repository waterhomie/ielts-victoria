# Examiner Victoria V2

V2 is the migration path from the Streamlit prototype to a real chat-product
architecture:

- React frontend for the iOS/WeChat-style chat experience.
- Python FastAPI backend for IELTS test state, feedback, transcription, TTS, and reports.
- Stateless API contract: the frontend sends the current `ExamSession`, and the backend
  returns the updated session. This keeps deployment simple and avoids server-side session
  loss across instances.

The original Streamlit app remains the stable production fallback. V2 is built beside it
instead of replacing it immediately.

## Why V2 exists

Streamlit is excellent for fast prototypes, but it reruns the whole script after each
interaction. That makes it difficult to build a truly native chat interface with:

- a fixed bottom composer,
- local message-list updates,
- mobile-first recording behavior,
- iOS-style interaction polish,
- frontend-controlled audio capture.

V2 moves those responsibilities into React and leaves Python to handle AI logic.

Related docs:

- [API contract](./API_CONTRACT.md)
- [Deployment plan](./DEPLOYMENT.md)

## Directory structure

```text
v2/
|-- backend/
|   |-- app.py              # FastAPI routes
|   |-- engine.py           # IELTS state machine and AI logic
|   |-- schemas.py          # Pydantic request/response/session models
|   |-- smoke_test.py       # API route smoke test
|   `-- requirements.txt    # Backend dependencies
`-- frontend/
    |-- package.json        # React/Vite project
    |-- vite.config.js      # Local dev proxy to Python API
    `-- src/
        |-- App.jsx         # iOS-style chat UI
        |-- api.js          # API client
        |-- recorder.js     # Browser WAV recorder
        `-- styles.css      # Mobile-first visual system
```

## Local development

Recommended Windows scripts from the repository root:

```powershell
.\v2\scripts\run_backend.ps1
```

Open a second terminal:

```powershell
.\v2\scripts\run_frontend.ps1
```

Run all local checks:

```powershell
.\v2\scripts\check_v2.ps1
```

If Windows blocks PowerShell scripts, run them with:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\v2\scripts\check_v2.ps1
```

Manual backend command:

```powershell
cd <repo-root>
python -m pip install -r v2/backend/requirements.txt
$env:API_KEY="your-key"
$env:BASE_URL="https://api.gptsapi.net/v1"
$env:MODEL="gpt-5.4-mini"
$env:CORS_ORIGINS="http://localhost:5173"
$env:MAX_AUDIO_UPLOAD_MB="12"
python -m uvicorn v2.backend.app:app --reload --host 0.0.0.0 --port 8000
```

Manual backend smoke test:

```powershell
cd <repo-root>
python -m v2.backend.smoke_test
```

Manual frontend command:

```powershell
cd v2/frontend
pnpm install
pnpm run dev
```

Open:

```text
http://localhost:5173
```

## Current V2 capabilities

- Starts a new IELTS speaking session.
- Displays messages in a real React chat panel.
- Uses a fixed iOS-style bottom composer.
- Supports typed answers.
- Supports tap-to-record / tap-to-send voice capture.
- Encodes browser audio as compact 16kHz mono WAV before transcription.
- Sends answers to the Python state machine.
- Supports dynamic Part 3 follow-up generation through the backend.
- Can request final scoring report from the backend.

## Still to finish before replacing Streamlit

- Live-test microphone permissions on iPhone Safari and WeChat in-app browser.
- Add proper authentication/rate limiting before public launch.
- Decide deployment target:
  - frontend: Vercel / Netlify / Cloudflare Pages
  - backend: Render / Railway / Fly.io / Cloud Run
- Add persistent practice history if user accounts become necessary.
- Set production `CORS_ORIGINS` to the deployed frontend domain.

## Verification already completed

- Python compile check for the V2 backend modules.
- Backend engine smoke test: start session -> identity answer -> Part 1 answer.
- FastAPI route smoke test with `python -m v2.backend.smoke_test`:
  `/api/health`, `/api/question-bank`, `/api/sessions`, `/api/answer`,
  and oversized audio rejection for `/api/transcribe`.
- Frontend dependency install with pnpm.
- Frontend production build with Vite.
- Question-bank validation from the existing app.
