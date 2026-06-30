# V2 deployment plan

V2 should be deployed as two services.

## Option A: simplest public deployment

Frontend:

- Vercel / Netlify / Cloudflare Pages
- Build command: `pnpm run build`
- Output directory: `dist`
- Root directory: `v2/frontend`
- Environment variable:

```text
VITE_API_BASE=https://your-backend-domain.com
```

Backend:

- Render / Railway / Fly.io / Google Cloud Run
- Root directory: repository root
- Install command:

```bash
python -m pip install -r v2/backend/requirements.txt
```

- Start command:

```bash
python -m uvicorn v2.backend.app:app --host 0.0.0.0 --port $PORT
```

- Environment variables:

```text
API_KEY=sk-...
BASE_URL=https://api.gptsapi.net/v1
MODEL=gpt-5.4-mini
TRANSCRIPTION_MODEL=whisper-1
CORS_ORIGINS=https://your-frontend-domain.com
MAX_AUDIO_UPLOAD_MB=12
RATE_LIMIT_PER_MINUTE=120
MAX_ANSWER_CHARS=4000
MAX_SESSION_MESSAGES=120
MAX_TTS_CHARS=1200
```

## Option B: one server serving both frontend and backend

This is possible later, but not the best first move. Keeping frontend and backend
separate is cleaner while the UI is changing quickly.

## Required production hardening

Before sharing V2 publicly:

1. Set backend `CORS_ORIGINS` to the real frontend domain instead of `*`.
2. Adjust `RATE_LIMIT_PER_MINUTE` for your expected traffic and budget.
3. Adjust `MAX_ANSWER_CHARS`, `MAX_SESSION_MESSAGES`, and `MAX_TTS_CHARS` if you change test length.
4. Keep API keys only in backend environment variables.
5. Test iPhone Safari and WeChat in-app browser microphone behavior.
6. Add a fallback typed-answer path when microphone permission is denied.

## Deployment handoff checklist

Use this order when V2 is ready to leave local development:

1. Choose hosting providers:
   - Frontend: Vercel / Netlify / Cloudflare Pages.
   - Backend: Render / Railway / Fly.io / Google Cloud Run.
2. Deploy the backend first with `API_KEY`, `BASE_URL`, `MODEL`, and safety-limit
   environment variables configured server-side only.
3. Temporarily set `CORS_ORIGINS` to the frontend preview domain during testing.
4. Run the backend health check:

```text
https://your-backend-domain.com/api/health
```

5. Deploy the frontend with:

```text
VITE_API_BASE=https://your-backend-domain.com
```

6. Replace `CORS_ORIGINS` with the final frontend production domain.
7. Run the deployment smoke-check script against both URLs.
8. Test one full IELTS flow on desktop Chrome.
9. Test microphone permission and recording on:
   - iPhone Safari
   - Android Chrome
   - WeChat in-app browser, if the app will be shared there
10. Keep the Streamlit app public until the above checks pass.

## Deployment smoke check

After deploying both services, run:

```powershell
.\v2\scripts\check_deployed_v2.ps1 `
  -BackendUrl "https://your-backend-domain.com" `
  -FrontendUrl "https://your-frontend-domain.com"
```

This checks backend health, CORS preflight, question-bank counts, practice
options, the core session/answer API flow, and frontend HTML availability.

## Current deployment recommendation

Keep Streamlit as the public stable version for now.

Use V2 privately until:

- mobile recording is verified,
- the backend is deployed,
- the frontend is deployed,
- CORS is restricted,
- and at least one full IELTS flow reaches the final report.
