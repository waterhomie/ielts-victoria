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

## Readiness snapshot

Current recommendation:

- Keep the original Streamlit app as the stable public fallback.
- Treat V2 as the custom React/FastAPI successor and private-beta build.
- Do not replace the public Streamlit link until V2 frontend and backend are deployed
  as real services and mobile microphone behavior is live-tested.

Ready now:

- Local React/FastAPI development flow.
- Stateless backend API for IELTS session state.
- Question-bank validation, backend smoke tests, and frontend production build.
- Custom chat UI, tap-to-record voice input, transcription, TTS playback, scoring reports,
  practice-record export, and focused practice modes.

Still required before public replacement:

- Hosted backend with protected environment variables.
- Hosted frontend with `VITE_API_BASE` pointing to the backend.
- Production `CORS_ORIGINS` restricted to the frontend domain.
- iPhone Safari and WeChat in-app-browser microphone testing.
- Budget-aware rate-limit tuning for the real API provider.

Intentionally not included yet:

- User accounts or database-backed history.
- Payment, subscription, or WeChat Mini Program release.
- Formal acoustic pronunciation scoring.
- Human tutor review or marketplace features.

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

Start both backend and frontend in the background:

```powershell
.\v2\scripts\run_local_stack.ps1
```

After dependencies are already installed, add `-SkipInstall` for faster restarts.

Stop the background stack:

```powershell
.\v2\scripts\stop_local_stack.ps1
```

Or run backend and frontend in separate terminals:

```powershell
.\v2\scripts\run_backend.ps1
```

Open a second terminal:

```powershell
.\v2\scripts\run_frontend.ps1
```

Both single-service scripts also support `-SkipInstall`.

Run all local checks:

```powershell
.\v2\scripts\check_v2.ps1
```

For repeat checks with the cached local dependencies, use `.\v2\scripts\check_v2.ps1 -SkipInstall`.

Check a deployed frontend/backend pair:

```powershell
.\v2\scripts\check_deployed_v2.ps1 `
  -BackendUrl "https://your-backend-domain.com" `
  -FrontendUrl "https://your-frontend-domain.com"
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
$env:RATE_LIMIT_PER_MINUTE="120"
$env:MAX_ANSWER_CHARS="4000"
$env:MAX_SESSION_MESSAGES="120"
$env:MAX_TTS_CHARS="1200"
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
- Supports Full, Part 1, Part 2, and Part 3 focused practice modes.
- Supports random or selected Part 1 topics and Part 2/3 cue cards for focused practice.
- Displays messages in a real React chat panel.
- Uses a fixed iOS-style bottom composer.
- Shows a live practice summary for answered turns, average WPM, timed duration, and voice/text usage.
- Includes mobile/PWA basics: viewport-fit, theme color, manifest, and lightweight app icon.
- Supports typed answers.
- Supports tap-to-record / tap-to-send voice capture.
- Encodes browser audio as compact 16kHz mono WAV before transcription.
- Sends answers to the Python state machine.
- Supports dynamic Part 3 follow-up generation through the backend.
- Shows a refresh-safe Part 2 preparation countdown when the long-turn cue card starts.
- Can request a current scoring report from the backend before or after completing the full test.
- Falls back to a rule-based report if the scoring model is temporarily unavailable.
- Adds a rule-based session learning summary to every report using only raw answers and timing data.
- Can download the final report, full transcript, and a combined practice record as plain text files.
- Renders report headings, lists, quotes, and inline examples cleanly in the React UI.
- Splits generated reports into focused cards for score, issues, examples, next tasks, and session summary.
- Adds quick navigation chips for long generated reports without changing downloaded text files.
- Keeps voice playback single-channel so restarting or answering stops any previous prompt audio.
- Checks backend health on startup and turns timeout/backend failures into clear UI errors.
- Includes a simple backend rate limit for public-deployment safety.
- Limits oversized answers, sessions, and TTS requests before they reach provider backends.
- Saves the current practice session locally on a best-effort basis so a refresh can restore the conversation.
- Local check scripts automatically load the cached backend dependencies under `tmp/v2_backend_deps` when present.

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
- PowerShell parse check for all V2 helper scripts.
- GitHub Actions workflow file prepared locally for V2 Python validation, question-bank validation,
  backend smoke test, frontend dependency install, and frontend production build. Publishing this
  workflow requires a GitHub token with `workflow` scope.
- Backend engine smoke test: start session -> identity answer -> Part 1 answer.
- Local stack helper smoke test on alternate ports: backend health and frontend HTTP status.
- Deployment smoke-check helper for backend/frontend URLs, CORS, question bank, and core API flow.
- FastAPI route smoke test with `python -m v2.backend.smoke_test`:
  `/api/health`, `/api/question-bank`, `/api/sessions`, `/api/answer`,
  report fallback behavior, oversized audio rejection for `/api/transcribe`,
  user-safe 502 messages for transcription/TTS provider failures, and report learning-summary output.
- Frontend dependency install with pnpm.
- Frontend production build with Vite.
- Question-bank validation from the existing app.
- Browser startup check against the local V2 frontend after backend health guard changes.
