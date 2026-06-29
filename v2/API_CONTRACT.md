# V2 API contract

Base URL in local development:

```text
http://localhost:8000
```

## GET /api/health

Checks backend availability.

Response:

```json
{
  "status": "ok",
  "app": "examiner-victoria-v2"
}
```

## GET /api/question-bank

Returns the question-bank counts currently loaded by the backend. This is a
small sanity-check endpoint for deployment and debugging.

Response:

```json
{
  "part1_topics": 32,
  "part1_secondary_topics": 30,
  "part1_total_questions": 152,
  "part1_secondary_questions": 139,
  "part1_identity_followup_questions": 13,
  "part2_base_cards": 3,
  "part2_extra_cards": 70,
  "part2_total_cards": 73,
  "part2_expected_cards": 73,
  "part3_reference_questions": 383
}
```

## POST /api/sessions

Starts a new IELTS speaking session.

Request:

```json
{
  "practice_mode": true,
  "answer_expansion_mode": true,
  "voice_playback_enabled": true
}
```

Response:

```json
{
  "session": {
    "session_id": "...",
    "phase": "identity",
    "messages": [
      {
        "role": "assistant",
        "content": "**Part 1 - Introduction and Interview**...",
        "phase": "identity"
      }
    ],
    "current_question": "...",
    "test_active": true
  }
}
```

The real session object contains additional fields for Part 1, Part 2, Part 3,
answer stats, and candidate answer logs. The frontend should keep and resend the
whole session object.

## POST /api/answer

Submits one typed or transcribed answer.

Request:

```json
{
  "session": { "...": "full current session object" },
  "answer": "I'm a student.",
  "source": "text",
  "duration": null
}
```

For recorded answers:

```json
{
  "session": { "...": "full current session object" },
  "answer": "I'm a student.",
  "source": "audio",
  "duration": 4.2
}
```

Response:

```json
{
  "session": { "...": "updated session object" },
  "assistant_message": {
    "role": "assistant",
    "content": "What do you study?",
    "phase": "part1"
  },
  "spoken_text": "What do you study?",
  "start_prep_timer": false
}
```

## POST /api/transcribe

Transcribes one audio file. The current frontend sends compact 16kHz mono WAV.

Request:

```text
multipart/form-data
file=answer.wav
```

Response:

```json
{
  "text": "I'm a student."
}
```

## POST /api/tts

Generates speech audio for a short assistant prompt.

Request:

```json
{
  "text": "What do you study?"
}
```

Response:

```text
audio/mpeg
```

## POST /api/report

Generates a final IELTS report from the session's raw candidate answers.

Request:

```json
{
  "session": { "...": "full current session object" }
}
```

Response:

```json
{
  "report": "Estimated overall band..."
}
```

## Stateless session rule

The backend does not currently store sessions in a database. The frontend must:

1. Keep the latest `session` object.
2. Send the full object with every `/api/answer` and `/api/report` request.
3. Replace local session state with the response session.

This keeps V2 easy to deploy while the product is still changing quickly.
