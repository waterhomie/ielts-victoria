# Examiner Victoria｜AI IELTS Speaking Coach

## 1. Product definition

Examiner Victoria is an AI IELTS Speaking practice web app for Chinese IELTS learners.

It is not a free-form chatbot. It is a structured speaking-practice system that follows the IELTS Speaking flow, gives spoken-English feedback, and helps the learner turn Chinese-thinking ideas into natural English expression.

Core product promise:

> Help IELTS candidates practise speaking with a realistic examiner flow, while receiving concise coaching on spoken grammar, semantic precision, and more natural expression.

## 2. Target users

- Chinese IELTS candidates who lack regular English-speaking practice.
- Learners who can express ideas in Chinese but struggle to find precise, natural English wording.
- Learners who need repeated practice with Part 1, Part 2, and Part 3 question types.

## 3. Current app structure

Main app file:

- `speaking_bot.app.py` on GitHub
- Local working source: `speaking_bot_reviewed.py`

Question bank files:

- `question_bank.py`
- `pdf_recall_question_bank.py`

Validation:

- `validate_question_bank.py`

Deployment:

- GitHub repository: `https://github.com/waterhomie/ielts-victoria`
- Streamlit Cloud app: `https://speakingbotapppy-bvxutvuemlfzbntfydvfrd.streamlit.app`

## 4. Technical stack

- Python
- Streamlit
- OpenAI-compatible LLM API through configured `BASE_URL`
- `whisper-1` compatible speech-to-text endpoint
- `gTTS` for text-to-speech playback
- Streamlit Cloud
- GitHub
- Streamlit Secrets

Configurable Secrets:

- `API_KEY`
- `BASE_URL`
- `MODEL`
- `TRANSCRIPTION_MODEL`

## 5. Current speaking flow

The app controls the IELTS Speaking flow through Streamlit session state.

Current phases:

1. `identity`
2. `part1`
3. `part2_long`
4. `part2_followup`
5. `part3`
6. `complete`

Expected flow:

```text
Identity check
→ Part 1 - Introduction and Interview
→ Part 2 - Long Turn
→ Part 2 follow-up
→ Part 3 - Discussion
→ Final report
```

The user should never need to say “continue” to move to the next IELTS stage.

The app should never ask the learner to choose Part 1, Part 2, or Part 3 during a normal full test. The program controls the stage.

## 6. Practice mode and mock-test mode

Practice mode is enabled by default.

When practice mode is on:

- Victoria gives instant spoken-English correction.
- Victoria may suggest a more precise expression.
- Victoria may provide a natural upgraded version of the learner’s answer.
- Part 3 uses a slightly longer training format.

When practice mode is off:

- Victoria should behave more like a real IELTS examiner.
- Feedback should mainly be provided at the end.
- Part 3 should be closer to a 4–5 minute discussion.

## 7. Feedback rules

Victoria should correct spoken English, not written transcript formatting.

Do correct:

- Audible grammar problems
- Spoken word-choice problems
- Awkward sentence structure
- Fluency or coherence issues
- Vague or inaccurate vocabulary when a more precise expression better matches the learner’s intended meaning

Do not correct:

- Capitalization
- Punctuation
- Pure spelling mistakes
- Proper-name capitalization
- Obvious speech-to-text noise
- Natural short answers that are acceptable in spoken IELTS

Feedback format:

```text
Quick correction
Better expression
A natural version of your answer
Next IELTS question
```

The feedback must not interrupt the test flow.

For long answers, practice mode may give up to three high-impact corrections.
For very short answers, answer upgrades should not invent new motivations, personal
history, or future plans that the learner did not express.

## 8. Part 3 question logic

Part 3 should be based on:

1. The selected Part 2 cue card
2. The question bank’s related Part 3 reference questions
3. The candidate’s Part 2 answer and follow-up answer
4. The candidate’s previous Part 3 answer

Current behavior:

- Practice mode: up to 6 main Part 3 questions
- Mock-test mode: about 4 main Part 3 questions
- Generate each Part 3 question dynamically after reading the previous Part 3 answer.
- Use the learner’s answer depth to decide whether to ask for clarification, comparison, cause, consequence, social impact, or future change.
- Fall back to reference bank questions if dynamic generation fails.
- Avoid repeating the same discussion angle under different wording, such as asking
  benefits/drawbacks immediately after advantages/disadvantages.
- If the candidate says they do not understand a Part 3 question, rephrase the
  current question instead of counting it and moving to the next one.

## 9. Question bank

Current verified bank:

- 32 Part 1 topics
- 152 Part 1 questions
- 73 Part 2 cue cards in the app
- 371 Part 3 reference questions in the bank

Before changing the question bank, run:

```bash
python validate_question_bank.py
```

The question bank should not be manually edited without validation.

## 10. Audio and privacy

The app may process:

- Typed answers
- Browser audio recordings
- Transcribed text
- Practice reports

The current input interface uses a custom frontend voice composer instead of
Streamlit's native `st.audio_input`:

- Voice mode by default
- tap-to-record / tap-to-send interaction for safer mobile use
- frontend WAV encoding from browser microphone audio instead of relying on
  browser-specific WebM/MP4 containers
- compact 16kHz mono audio upload for transcription
- automatic audio upload to Python after recording stops
- Whisper-compatible transcription in Python
- optional transcript review before submission
- Type mode with a small text input
- iOS-style fixed bottom composer on mobile/desktop

This avoids the native Streamlit recorder problem where the previous recording
can remain visible after the next question appears.

Privacy rule:

> Recordings and transcripts may be sent to the configured API provider for transcription, feedback, and speech playback. The app should communicate this clearly to users.

The API key must never be hard-coded in public source code.

## 11. Final report rules

The final IELTS report should score only the candidate’s raw answers.

It must not score:

- Victoria’s corrections
- Victoria’s upgraded answers
- Victoria’s prompts
- The identity/full-name answer unless it contains meaningful spoken-English evidence

The final report should include:

1. Estimated overall band score
2. Estimated scores for major IELTS speaking dimensions
3. Recurring spoken-language problems
4. Natural corrected examples
5. Better-expression examples
6. Three focused next-practice tasks based on the transcript

A generic seven-day plan should not be the default report output.

Pronunciation should not be assessed confidently unless acoustic analysis is implemented.

## 12. Current non-goals

The app currently does not include:

- User accounts
- Database-backed practice history
- WeChat Mini Program frontend
- Payment
- Human tutor review
- Formal pronunciation scoring
- Full writing-material management
- Full speaking-material library management

These may be future product directions, but they should not be mixed into the core IELTS Speaking Loop until the basic practice loop is stable.

## 13. Product direction

The next major product evolution is not “more pages”.

The next important step is to make the training loop smarter:

```text
Observe learner answer
→ Identify weakness
→ Give concise feedback
→ Ask the next best question
→ Record recurring problem
→ Use the record in the next practice session
```

The long-term product direction is:

> A learner-aware AI IELTS Speaking Coach that remembers recurring weaknesses and trains the learner through structured, verifiable speaking loops.
