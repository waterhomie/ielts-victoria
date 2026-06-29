from __future__ import annotations

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .engine import (
    build_report,
    get_question_bank_summary,
    process_answer,
    start_session,
    synthesize_speech,
    transcribe_audio,
)
from .schemas import (
    AnswerRequest,
    AnswerResponse,
    ReportRequest,
    ReportResponse,
    StartSessionRequest,
    StartSessionResponse,
    TTSRequest,
    TranscriptionResponse,
)


app = FastAPI(
    title="Examiner Victoria V2 API",
    version="0.1.0",
    description="Python API backend for the React/iOS-style IELTS speaking coach.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "examiner-victoria-v2"}


@app.get("/api/question-bank")
def question_bank() -> dict[str, int]:
    return get_question_bank_summary()


@app.post("/api/sessions", response_model=StartSessionResponse)
def create_session(request: StartSessionRequest) -> StartSessionResponse:
    session = start_session(
        practice_mode=request.practice_mode,
        answer_expansion_mode=request.answer_expansion_mode,
        voice_playback_enabled=request.voice_playback_enabled,
    )
    return StartSessionResponse(session=session)


@app.post("/api/answer", response_model=AnswerResponse)
def answer_question(request: AnswerRequest) -> AnswerResponse:
    answer = request.answer.strip()
    if not answer:
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")
    session, assistant_message, spoken_text, start_prep_timer = process_answer(
        request.session,
        answer,
        source=request.source,
        duration=request.duration,
    )
    return AnswerResponse(
        session=session,
        assistant_message=assistant_message,
        spoken_text=spoken_text,
        start_prep_timer=start_prep_timer,
    )


@app.post("/api/transcribe", response_model=TranscriptionResponse)
async def transcribe(
    file: UploadFile = File(...),
    content_type: str | None = Header(default=None),
) -> TranscriptionResponse:
    audio_bytes = await file.read()
    mime_type = file.content_type or content_type or "audio/wav"
    try:
        text = transcribe_audio(audio_bytes, mime_type)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {error}") from error
    return TranscriptionResponse(text=text)


@app.post("/api/tts")
def tts(request: TTSRequest) -> Response:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    try:
        audio = synthesize_speech(request.text)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"TTS failed: {error}") from error
    return Response(content=audio, media_type="audio/mpeg")


@app.post("/api/report", response_model=ReportResponse)
def report(request: ReportRequest) -> ReportResponse:
    return ReportResponse(report=build_report(request.session))
