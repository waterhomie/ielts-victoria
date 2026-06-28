# Development Progress

Last updated: 2026-06-28

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
  - 371 Part 3 reference questions in bank
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
- Part 3 questions are generated as a batch before Part 3 starts; a stronger loop would generate each next question after reading the previous answer.
- There is no persistent learner profile, so the app does not remember weaknesses across sessions.
- There is no database or user account system.
- TTS depends on `gTTS`, which may be slow or unavailable sometimes.
- The local working folder is not a fully normal Git checkout, so updates have often been pushed through GitHub API.
- The app relies on a third-party OpenAI-compatible API provider.
- Public commercial launch would require more privacy, compliance, payment, and content-safety work.

## High-priority backlog

1. Dynamic Part 3 loop
   - Generate one Part 3 question at a time.
   - Use the previous Part 3 answer to decide the next question.
   - Keep a hard maximum question count.
   - Fall back to bank questions if model generation fails.

2. Learner profile / session learning summary
   - Summarize recurring weaknesses after each practice session.
   - Save:
     - common grammar issues
     - vague vocabulary
     - weak answer development
     - Part 3 reasoning problems
     - next-session focus

3. Refactor state machine
   - Split `process_candidate_answer` into:
     - `handle_identity`
     - `handle_part1`
     - `handle_part2_long`
     - `handle_part2_followup`
     - `handle_part3`

4. README / portfolio polish
   - Add project overview.
   - Add screenshots.
   - Add feature list.
   - Add technical architecture.
   - Add development-loop explanation.

5. GitHub Actions validation
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

> Implement dynamic Part 3 question generation one question at a time.

Acceptance criteria:

1. Part 3 no longer has to generate all questions before the discussion starts.
2. After each Part 3 answer, the app decides the next question based on:
   - selected cue card
   - reference Part 3 bank
   - previous Part 3 answer
   - full Part 2 answer
3. Practice mode still allows a longer Part 3.
4. Mock-test mode remains shorter.
5. There is a hard maximum question count.
6. If model generation fails, fallback questions from the bank are used.
7. `python -m py_compile` passes.
8. `python validate_question_bank.py` passes.

## Notes for future AI collaborators

Before changing code:

1. Read `PROJECT_SPEC.md`.
2. Read this `progress.md`.
3. Read `DEVELOPMENT_LOOP.md`.
4. Make one focused change at a time.
5. Run validation before deployment.
