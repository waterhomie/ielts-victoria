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

It is not yet ready for:

- Paid public launch
- WeChat Mini Program release
- Large-scale user data storage
- Formal pronunciation assessment

## Current risks

- `process_candidate_answer` is still large and should eventually be split into stage-specific handlers.
- Part 3 dynamic generation now depends on model quality; fallback bank questions are used when generation fails.
- The app now uses a custom frontend voice composer. Further polish may still be needed after live browser testing, especially around microphone permissions and mobile touch behavior.
- There is no persistent learner profile, so the app does not remember weaknesses across sessions.
- There is no database or user account system.
- TTS depends on `gTTS`, which may be slow or unavailable sometimes.
- The local working folder is not a fully normal Git checkout, so updates have often been pushed through GitHub API.
- The app relies on a third-party OpenAI-compatible API provider.
- Public commercial launch would require more privacy, compliance, payment, and content-safety work.

## High-priority backlog

1. Learner profile / session learning summary
   - Summarize recurring weaknesses after each practice session.
   - Save:
     - common grammar issues
     - vague vocabulary
     - weak answer development
     - Part 3 reasoning problems
     - next-session focus

2. Refactor state machine
   - Split `process_candidate_answer` into:
     - `handle_identity`
     - `handle_part1`
     - `handle_part2_long`
     - `handle_part2_followup`
     - `handle_part3`

3. README / portfolio polish
   - Add project overview.
   - Add screenshots.
   - Add feature list.
   - Add technical architecture.
   - Add development-loop explanation.

4. GitHub Actions validation
   - Run Python syntax check.
   - Run `validate_question_bank.py`.
   - Prevent broken changes from being deployed.

## Medium-priority backlog

- Add practice-history export format.
- Add report markdown formatting improvements.
- Add selectable practice types:
  - Full mock test
  - Part 1 only
  - Part 2 only
  - Part 3 only
- Add topic/category selection.
- Add better Part 2 timer behavior.
- Add more visible loading states.
- Add clearer error messages for API failure.
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

> Add a learner profile / session learning summary that records recurring weaknesses and suggests the next-session focus.

Acceptance criteria:

1. The app summarizes recurring grammar, vocabulary, fluency, and answer-development weaknesses after a session.
2. The summary is based only on the candidate's raw answers and timing data.
3. The summary can be exported with the final report.
4. The app does not store personal data outside the current session unless the user explicitly exports it.
5. `python -m py_compile` passes.
6. `python validate_question_bank.py` passes.

## Notes for future AI collaborators

Before changing code:

1. Read `PROJECT_SPEC.md`.
2. Read this `progress.md`.
3. Read `DEVELOPMENT_LOOP.md`.
4. Make one focused change at a time.
5. Run validation before deployment.
