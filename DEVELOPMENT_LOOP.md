# AI Development Loop for Examiner Victoria

This file defines how AI coding assistants should work on this project.

The goal is not to “just modify code”. The goal is to run a safe, inspectable development loop:

```text
Read project memory
→ choose one concrete goal
→ define acceptance criteria
→ modify only relevant files
→ run checks
→ review risks
→ deploy or report blocker
→ update progress
```

## 1. Always start by reading project memory

Before making code changes, read:

1. `PROJECT_SPEC.md`
2. `progress.md`
3. `DEVELOPMENT_LOOP.md`

These files are the project’s external memory.

Do not rely only on conversation history.

## 2. Clarify the development goal

Each development loop should have one main goal.

Good goal:

```text
Make final IELTS reports score only raw candidate answers, not AI upgraded answers.
```

Bad goal:

```text
Optimize the app.
```

If the user gives a vague goal, turn it into a concrete task before editing.

## 3. Define acceptance criteria

Every task should have acceptance criteria.

Example:

```text
Goal:
Make Part 3 generate the next question dynamically after each answer.

Acceptance criteria:
1. The app stores Part 3 answer history.
2. The next Part 3 question is generated after each answer.
3. The generator uses the cue card, bank questions, and previous answers.
4. The app has a hard maximum Part 3 question count.
5. It falls back to bank questions if model generation fails.
6. Python syntax check passes.
7. Question bank validation passes.
```

## 4. Work in small steps

Prefer small, safe changes.

Do not combine unrelated changes such as:

- state-machine refactor
- UI redesign
- question-bank rewrite
- API-provider change
- payment feature

in one loop.

One loop should usually touch one conceptual area.

## 5. Protect secrets and user data

Never hard-code:

- API keys
- tokens
- passwords
- private URLs
- user personal data

Use Streamlit Secrets for runtime configuration:

- `API_KEY`
- `BASE_URL`
- `MODEL`
- `TRANSCRIPTION_MODEL`

Do not print secrets in logs or final answers.

## 6. Preserve IELTS product behavior

When changing the app, preserve these product rules:

- The app controls IELTS stages.
- The user should not need to say “continue”.
- The app should not ask the learner to choose Part 1, Part 2, or Part 3 during a normal full test.
- Practice mode can give feedback during the test.
- Mock-test mode should feel more like a real IELTS speaking test.
- Feedback should not correct capitalization, punctuation, pure spelling, or speech-to-text noise.
- Final reports should score only raw candidate answers.

## 7. Required checks before deployment

Run:

```bash
python -m py_compile speaking_bot_reviewed.py question_bank.py pdf_recall_question_bank.py validate_question_bank.py
python validate_question_bank.py
```

If `python` is not available in PATH, use the bundled Codex Python runtime.

Expected question-bank validation currently reports:

```text
Question bank sanity check passed.
Part 1 topics: 32
Part 1 questions: 152
Part 2 bank cue cards: 70
Part 2 app total cue cards: 73
Part 3 reference questions: 371
```

## 8. Deployment rule

The Streamlit app uses GitHub as the source of truth.

The online app reads:

```text
speaking_bot.app.py
```

The local working source is often:

```text
speaking_bot_reviewed.py
```

When deploying, keep these in sync.

After pushing to GitHub, Streamlit Cloud should redeploy automatically.

## 9. Risk review before final response

Before telling the user the work is complete, check:

- Did syntax validation pass?
- Did question-bank validation pass?
- Did we touch only intended files?
- Did we avoid exposing secrets?
- Did we preserve the speaking flow?
- Did we avoid scoring AI-generated upgraded answers?
- Did we update `progress.md` if the development state changed?

## 10. Human-in-the-loop rule

Escalate to the user before:

- changing API provider
- deleting files
- changing payment/commercial logic
- adding public data collection
- changing privacy assumptions
- making large architecture rewrites
- publishing a new public release with user-facing risk

## 11. Good task prompt template for the user

The user can give future tasks like this:

```text
Goal:
<What should change?>

Why:
<What user problem does it solve?>

Acceptance criteria:
1. ...
2. ...
3. ...

Constraints:
- Do not change ...
- Keep ...
```

## 12. Current development philosophy

This project should grow through loops, not random feature piling.

Preferred loop:

```text
Use the app
→ notice a real problem
→ define the desired behavior
→ implement the smallest useful change
→ validate locally
→ deploy
→ test again
→ record what changed
```

The user does not need to be a traditional programmer.

The user’s role is:

- product owner
- tester
- requirement designer
- final judge of IELTS-learning usefulness

The AI assistant’s role is:

- code reader
- implementation partner
- validation runner
- deployment helper
- risk reporter
