# Development Progress

Last updated: 2026-06-29

## Completed

- Built Streamlit web app prototype for IELTS Speaking practice.
- Moved API key out of public code and into Streamlit Secrets.
- Configured OpenAI-compatible API access through `BASE_URL`.
- Added IELTS Speaking stage control with Streamlit `session_state`.
- Implemented phases:
  - `identity`
  - `part1`
  - `part2_long`
  - `part2_followup`
  - `part3`
  - `complete`
- Added automatic stage progression so the learner does not need to say “continue”.
- Added current-stage display in sidebar.
- Added practice mode and mock-test mode behavior.
- Added instant spoken-English correction in practice mode.
- Added semantic expression coaching through `Better expression`.
- Added natural answer upgrade while preserving the learner’s intended meaning.
- Added Part 3 adaptive question generation from question bank plus Part 2 answers.
- Changed Part 3 into a dynamic one-question-at-a-time loop that uses the previous Part 3 answer before generating the next question.
- Added Part 3 discussion-angle de-duplication so benefits/drawbacks style questions are not repeated under different wording.
- Added clarification handling in Part 3: if the learner says they do not understand, Victoria rephrases the current question instead of moving on.
- Added Part 1 topic-transition wording such as "Let's talk about gifts" before switching topics.
- Improved feedback behavior for long answers so practice mode can return up to three high-impact corrections.
- Tightened answer-upgrade rules so Victoria does not invent motivations, histories, or future plans for very short answers.
- Changed the default final report from a generic seven-day plan to three transcript-specific next practice tasks.
- Made the recorder section more visible and clearer by default.
- Replaced Streamlit's native `st.audio_input` with a custom frontend voice composer:
  hold-to-speak recording, automatic upload after recording stops, optional transcript review,
  and compact Type mode in the same component.
- Added a turn reset token and post-answer rerun so the composer clears after each response
  and reappears under the latest examiner question instead of leaving the previous recording
  UI in the middle of the conversation.
- Changed the voice composer from hold-to-speak to tap-to-record / tap-to-send, which is
  safer on mobile browsers because long-press gestures can trigger native selection menus.
- Reworked the browser recorder to generate compact 16kHz mono WAV audio in the frontend,
  reducing mobile audio container issues such as failed duration parsing from iOS/WebView
  recordings.
- Added mobile-oriented iOS-style polish: glassy fixed bottom composer, safer touch behavior,
  and smaller mobile title/layout spacing.
- Suppressed "A natural version of your answer" when the candidate's answer is already
  natural or nearly identical to the suggested rewrite, avoiding fake-looking feedback.
- Started V2 as a side-by-side architecture instead of continuing to overfit Streamlit:
  `v2/backend` now contains a FastAPI-style stateless exam API and reusable IELTS
  state engine; `v2/frontend` now contains a React/Vite iOS-style chat UI with a fixed
  bottom composer and tap-to-record WAV capture. The Streamlit app remains the stable
  fallback while V2 matures.
- Fixed V2 question-bank coverage so Part 2 now samples from the full app set:
  3 built-in cue cards plus 70 extended/PDF cue cards.
- Added V2 `/api/question-bank` sanity endpoint and smoke-test checks for question-bank counts.
- Improved V2 mobile composer behavior with friendlier transcription errors, cleaner recorder
  reset after each answer, stable letter avatars, and an app-like internal chat scroll panel.
- Added V2 deployment hardening: environment-driven CORS allowlist, audio upload size limit,
  oversized-audio smoke-test coverage, and safer mobile recorder cleanup on page hide.
- Added V2 short/empty-audio guards in both frontend and backend so mobile recording glitches
  return a friendly retry message instead of raw transcription-provider errors.
- Refined V2 mobile composer details: visible `review` control on narrow screens, smaller
  mobile title spacing, and verified fixed bottom input behavior in a phone-sized viewport.
- Added V2 frontend backend-health guard and request timeout handling so deployment/API
  configuration failures show clear recovery messages instead of hanging silently.
- Added V2 local stack scripts to start/stop the React frontend and FastAPI backend together
  with logs, PID tracking, port checks, and health/status verification.
- Added V2 final-report and transcript text downloads from the React report screen.
- Added V2 mobile/PWA basics: app manifest, theme metadata, iOS web-app metadata, and
  lightweight SVG app icon.
- Added V2 rule-based final-report fallback so `/api/report` returns useful practice
  guidance even when the model/API key is temporarily unavailable.
- Added V2 deployed-environment smoke-check script for backend health, question-bank counts,
  and frontend HTML availability.
- Added V2 backend in-memory rate limiting with `RATE_LIMIT_PER_MINUTE` to reduce accidental
  public API abuse during early deployment.
- Added V2 best-effort local session persistence via `localStorage` so accidental refreshes
  can restore the current conversation, report, audio preference, and transcript-review setting.
- Hardened the V2 local check script so it automatically loads cached backend dependencies
  from `tmp/v2_backend_deps` before running FastAPI smoke tests.
- Replaced raw transcription/TTS provider 502 details with short user-safe messages and
  smoke-test coverage, so mobile users do not see internal provider errors.
- Added single-channel V2 voice playback handling so restart, sound-off, or a new answer
  stops any previous prompt audio before continuing.
- Added `-SkipInstall` support to the single-service V2 backend/frontend run scripts and
  reused the local dependency path for faster developer restarts.
- Added PowerShell helper-script parse checks to the V2 validation script so script syntax
  regressions are caught with the regular local checks.
- Added a V2 Part 2 preparation countdown that is driven by the backend state transition
  and preserved by the frontend's local session persistence.
- Added a V2 `Score` action so learners can generate a current report before completing
  the entire mock test; old reports clear automatically when the learner continues answering.
- Added backend payload-size guards for oversized answers and oversized client sessions to
  reduce accidental public-deployment cost and abuse risk.
- Added a V2 `MAX_TTS_CHARS` guard so oversized voice-playback requests are rejected
  before reaching the TTS provider.
- Refined V2 frontend error mapping so rate-limit and oversized-payload messages remain
  specific instead of being mistaken for generic transcription failures.
- Expanded the V2 deployment smoke check to verify CORS preflight and a real
  session-start/identity-answer API flow in addition to health, question bank, and frontend HTML.
- Fixed V2 frontend helper scripts so custom dev ports are honored reliably through
  `pnpm exec vite`, then verified the local stack on alternate ports.
- Added a rule-based V2 session learning summary to every report/export, using only
  raw candidate answers and timing data to identify recurring weaknesses and the next-session focus.
- Refactored the V2 answer state machine so identity, Part 1, Part 2 long-turn,
  Part 2 follow-up, and Part 3 logic now live in smaller phase handlers while preserving behavior.
- Added V2 focused practice modes for Full, Part 1, Part 2, and Part 3, with
  frontend mode selection, backend session tracking, and focused-mode start phases.
- Added selectable Part 1 topics and Part 2/3 cue cards for focused practice, powered by
  a new `/api/practice-options` endpoint while keeping random selection as the default.
- Added a V2 practice-record export that combines session metadata, selected topic/cue card,
  timing/WPM stats, question-by-question answers, the full transcript, and any generated report.
- Improved V2 report formatting with structured Markdown output, richer React rendering for
  headings/lists/quotes/inline examples, and smoke coverage for the fallback report structure.
- Added focused report cards that split score, skill breakdown, issues, corrected examples,
  next-session tasks, and summary into mobile-friendly visual sections.
- Added optional quick-navigation chips for multi-section reports, using in-panel smooth
  scrolling and leaving downloaded text exports unchanged.
- Prepared a GitHub Actions V2 validation workflow for Python syntax, question-bank validation,
  FastAPI smoke tests, pnpm dependency install, and frontend production build. Remote publishing is
  pending because GitHub requires a token with `workflow` scope to create `.github/workflows/*`.
- Added a live V2 practice-summary panel for answered turns, average WPM, timed duration,
  and voice/text usage, with a compact 2x2 mobile layout.
- Improved voice fallback behavior so microphone permission errors or transcription failures
  automatically switch the composer to text mode.
- Improved text composer ergonomics with a compact textarea: Enter sends, Shift+Enter creates
  a new line, and the input still stays visually compact.
- Added V2 frontend/backend `.env.example` templates for safer deployment handoff without
  committing real API keys.
- Added safe V2 backend health diagnostics for model/configuration/limits and strengthened
  the deployed smoke check so missing `API_KEY` is caught before public testing.
- Adjusted Part 3 question count:
  - Practice mode: about 6 main questions
  - Mock-test mode: about 4 main questions
- Added browser audio recording through Streamlit.
- Added `whisper-1` compatible transcription.
- Added `gTTS` voice playback.
- Added voice playback toggle.
- Added full-feedback voice toggle.
- Added privacy notice in sidebar.
- Added WPM and speaking-time statistics for recorded answers.
- Added raw candidate-answer log so final reports do not score AI-generated upgraded answers.
- Updated final report logic to ignore identity answers by default.
- Added final report download.
- Added transcript download.
- Added `validate_question_bank.py`.
- Verified current question bank:
  - 32 Part 1 topics
  - 152 Part 1 questions
  - 73 Part 2 cue cards in app
  - 383 Part 3 reference questions in app
- Added version ranges in `requirements.txt`.
- Deployed through GitHub and Streamlit Cloud.

## Current known state

The app is a working IELTS Speaking practice prototype.

It is best described as:

> A structured AI IELTS Speaking Coach web app with stage control, question bank, voice input, transcription, TTS, instant coaching, and final report generation.

The current product is suitable for:

- Personal IELTS speaking practice
- Portfolio demonstration
- Small user testing
- V2 private beta testing after separate frontend/backend deployment

It is not yet ready for:

- Paid public launch
- WeChat Mini Program release
- Large-scale user data storage
- Formal pronunciation assessment
- Replacing the public Streamlit fallback before mobile microphone testing

## V2 deployment handoff checklist

1. Deploy the FastAPI backend with API secrets only in backend environment variables.
2. Deploy the React frontend with `VITE_API_BASE` pointing to the backend.
3. Restrict backend `CORS_ORIGINS` to the deployed frontend domain.
4. Run `v2/scripts/check_deployed_v2.ps1` against both services.
5. Complete one desktop full-flow test through final report generation.
6. Complete iPhone Safari, Android Chrome, and WeChat in-app-browser recording tests.
7. Keep the Streamlit version public until the V2 checks above pass.

## Current risks

- The state machine has been split into phase handlers, but more unit-level tests would make future changes safer.
- Part 3 dynamic generation now depends on model quality; fallback bank questions are used when generation fails.
- The app now uses a custom frontend voice composer. Further polish may still be needed after live browser testing, especially around microphone permissions and mobile touch behavior.
- There is no persistent learner profile, so the app does not remember weaknesses across sessions.
- There is no database or user account system.
- TTS depends on `gTTS`, which may be slow or unavailable sometimes.
- The local working folder is not a fully normal Git checkout, so updates have often been pushed through GitHub API.
- The app relies on a third-party OpenAI-compatible API provider.
- Public commercial launch would require more privacy, compliance, payment, and content-safety work.

## High-priority backlog

1. README / portfolio polish
   - Add project overview.
   - Add screenshots.
   - Add feature list.
   - Add technical architecture.
   - Add development-loop explanation.

2. CI follow-up
   - Reauthorize GitHub CLI with `workflow` scope.
   - Publish `.github/workflows/v2-checks.yml`.
   - Confirm the first GitHub Actions run passes on GitHub.
   - Add badges to README after the workflow is proven green.

## Medium-priority backlog

- Live mobile QA for iPhone Safari, Android Chrome, and WeChat in-app-browser recording.
- Deploy V2 frontend and backend as separate services and run the deployed smoke check.
- Add screenshots/GIFs for portfolio and README.
- Add optional persistent practice history once accounts or local export strategy is decided.
- Add a production-ready auth/rate-limit strategy before public monetization.
- Add optional model/provider configuration UI for advanced users.
- Add optional model selector through Streamlit Secrets or sidebar.

## Low-priority / future product ideas

- User accounts
- Database-backed practice history
- Speaking-material library
- Writing-material library
- Personal story bank for Part 2 reuse
- WeChat Mini Program frontend
- Payment / subscription
- Tutor marketplace or human-review upsell
- Pronunciation scoring with acoustic analysis

## Next recommended development loop

Recommended next task:

> Add app readiness/deployment status note.

Acceptance criteria:

1. README explains clearly that V2 is the custom React/FastAPI successor to the Streamlit app.
2. README lists what is production-ready, what still needs hosting configuration, and what is intentionally not included.
3. Progress notes include a concise deployment handoff checklist.
4. `python -m py_compile` passes.
5. `python validate_question_bank.py` passes.
6. Frontend production build passes.

## Notes for future AI collaborators

Before changing code:

1. Read `PROJECT_SPEC.md`.
2. Read this `progress.md`.
3. Read `DEVELOPMENT_LOOP.md`.
4. Make one focused change at a time.
5. Run validation before deployment.
