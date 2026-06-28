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
```

## Option B: one server serving both frontend and backend

This is possible later, but not the best first move. Keeping frontend and backend
separate is cleaner while the UI is changing quickly.

## Required production hardening

Before sharing V2 publicly:

1. Replace backend `allow_origins=["*"]` with the real frontend domain.
2. Add basic rate limiting to transcription and model endpoints.
3. Keep API keys only in backend environment variables.
4. Test iPhone Safari and WeChat in-app browser microphone behavior.
5. Add a fallback typed-answer path when microphone permission is denied.

## Current deployment recommendation

Keep Streamlit as the public stable version for now.

Use V2 privately until:

- mobile recording is verified,
- the backend is deployed,
- the frontend is deployed,
- CORS is restricted,
- and at least one full IELTS flow reaches the final report.

