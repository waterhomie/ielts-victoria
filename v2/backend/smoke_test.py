from __future__ import annotations

from fastapi.testclient import TestClient

import v2.backend.app as app_module
from v2.backend.app import app
from v2.backend.engine import build_fallback_report, build_session_learning_summary
from v2.backend.schemas import ExamSession


def main() -> None:
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200, health.text

    question_bank = client.get("/api/question-bank")
    assert question_bank.status_code == 200, question_bank.text
    bank = question_bank.json()
    assert bank["part2_total_cards"] == 73, bank
    assert bank["part2_total_cards"] == bank["part2_expected_cards"], bank

    practice_options = client.get("/api/practice-options")
    assert practice_options.status_code == 200, practice_options.text
    options = practice_options.json()
    assert len(options["part1_topics"]) >= 30, options
    assert len(options["cue_cards"]) == 73, options
    chosen_topic = options["part1_topics"][0]
    chosen_card = options["cue_cards"][0]["title"]

    oversized_audio = client.post(
        "/api/transcribe",
        files={"file": ("answer.wav", b"0" * (13 * 1024 * 1024), "audio/wav")},
    )
    assert oversized_audio.status_code == 413, oversized_audio.text

    tiny_audio = client.post(
        "/api/transcribe",
        files={"file": ("answer.wav", b"RIFF", "audio/wav")},
    )
    assert tiny_audio.status_code == 400, tiny_audio.text

    original_transcribe_audio = app_module.transcribe_audio
    try:
        def broken_transcribe_audio(_audio_bytes: bytes, _mime_type: str) -> str:
            raise RuntimeError("provider duration parse failed: internal detail")

        app_module.transcribe_audio = broken_transcribe_audio
        failed_audio = client.post(
            "/api/transcribe",
            files={"file": ("answer.wav", b"0" * 4096, "audio/wav")},
        )
        assert failed_audio.status_code == 502, failed_audio.text
        failed_detail = failed_audio.json()["detail"]
        assert "internal detail" not in failed_detail, failed_detail
        assert "temporarily unavailable" in failed_detail, failed_detail
    finally:
        app_module.transcribe_audio = original_transcribe_audio

    too_long_tts = client.post("/api/tts", json={"text": "a" * (app_module.MAX_TTS_CHARS + 1)})
    assert too_long_tts.status_code == 413, too_long_tts.text

    original_synthesize_speech = app_module.synthesize_speech
    try:
        def broken_synthesize_speech(_text: str) -> bytes:
            raise RuntimeError("provider voice error: internal detail")

        app_module.synthesize_speech = broken_synthesize_speech
        failed_tts = client.post("/api/tts", json={"text": "Hello"})
        assert failed_tts.status_code == 502, failed_tts.text
        failed_tts_detail = failed_tts.json()["detail"]
        assert "internal detail" not in failed_tts_detail, failed_tts_detail
        assert "temporarily unavailable" in failed_tts_detail, failed_tts_detail
    finally:
        app_module.synthesize_speech = original_synthesize_speech

    start = client.post(
        "/api/sessions",
        json={
            "practice_mode": True,
            "practice_type": "full",
            "answer_expansion_mode": True,
            "voice_playback_enabled": False,
        },
    )
    assert start.status_code == 200, start.text
    session = start.json()["session"]
    assert session["phase"] == "identity"

    part2_start = client.post(
        "/api/sessions",
        json={
            "practice_mode": True,
            "practice_type": "part2",
            "cue_card_title": chosen_card,
            "answer_expansion_mode": True,
            "voice_playback_enabled": False,
        },
    )
    assert part2_start.status_code == 200, part2_start.text
    part2_session = part2_start.json()["session"]
    assert part2_session["phase"] == "part2_long", part2_start.text
    assert part2_session["cue_card"]["title"] == chosen_card, part2_session

    part3_start = client.post(
        "/api/sessions",
        json={
            "practice_mode": True,
            "practice_type": "part3",
            "cue_card_title": chosen_card,
            "answer_expansion_mode": True,
            "voice_playback_enabled": False,
        },
    )
    assert part3_start.status_code == 200, part3_start.text
    part3_session = part3_start.json()["session"]
    assert part3_session["phase"] == "part3", part3_session
    assert part3_session["part3_questions"], part3_session
    assert part3_session["cue_card"]["title"] == chosen_card, part3_session

    topic_start = client.post(
        "/api/sessions",
        json={
            "practice_mode": True,
            "practice_type": "part1",
            "part1_topic": chosen_topic,
            "answer_expansion_mode": True,
            "voice_playback_enabled": False,
        },
    )
    assert topic_start.status_code == 200, topic_start.text
    assert topic_start.json()["session"]["part1_topic"] == chosen_topic, topic_start.text

    too_long_answer = client.post(
        "/api/answer",
        json={
            "session": session,
            "answer": "a" * (app_module.MAX_ANSWER_CHARS + 1),
            "source": "text",
            "duration": None,
        },
    )
    assert too_long_answer.status_code == 413, too_long_answer.text

    too_large_session = dict(session)
    too_large_session["messages"] = session["messages"] * (app_module.MAX_SESSION_MESSAGES + 1)
    too_large_report = client.post("/api/report", json={"session": too_large_session})
    assert too_large_report.status_code == 413, too_large_report.text

    answer1 = client.post(
        "/api/answer",
        json={
            "session": session,
            "answer": "You can call me Water.",
            "source": "text",
            "duration": None,
        },
    )
    assert answer1.status_code == 200, answer1.text
    session = answer1.json()["session"]
    assert session["phase"] == "part1"

    answer2 = client.post(
        "/api/answer",
        json={
            "session": session,
            "answer": "I'm a student.",
            "source": "text",
            "duration": None,
        },
    )
    assert answer2.status_code == 200, answer2.text
    session = answer2.json()["session"]
    assert session["messages"][-1]["role"] == "assistant"

    prep_signal_seen = False
    for _ in range(8):
        next_part1 = client.post(
            "/api/answer",
            json={
                "session": session,
                "answer": "I usually give a short answer with one reason.",
                "source": "text",
                "duration": None,
            },
        )
        assert next_part1.status_code == 200, next_part1.text
        next_payload = next_part1.json()
        session = next_payload["session"]
        if next_payload["start_prep_timer"]:
            prep_signal_seen = True
            break

    assert prep_signal_seen, session
    assert session["phase"] == "part2_long", session

    report = client.post("/api/report", json={"session": session})
    assert report.status_code == 200, report.text
    report_text = report.json()["report"]
    assert "Report generation failed" not in report_text, report_text
    assert len(report_text) > 80, report_text
    assert "Session learning summary" in report_text, report_text

    fallback_text = build_fallback_report(ExamSession.model_validate(session))
    assert "rule-based fallback" in fallback_text, fallback_text
    assert "Next-session practice tasks" in fallback_text, fallback_text
    assert "Session learning summary" in fallback_text, fallback_text

    summary_text = build_session_learning_summary(ExamSession.model_validate(session))
    assert "Evidence used" in summary_text, summary_text
    assert "Next-session focus" in summary_text, summary_text

    app_module.REQUEST_LOG.clear()
    original_rate_limit = app_module.RATE_LIMIT_PER_MINUTE
    try:
        app_module.RATE_LIMIT_PER_MINUTE = 1
        first_limited = client.post(
            "/api/sessions",
            json={
                "practice_mode": True,
                "answer_expansion_mode": True,
                "voice_playback_enabled": False,
            },
        )
        assert first_limited.status_code == 200, first_limited.text
        second_limited = client.post(
            "/api/sessions",
            json={
                "practice_mode": True,
                "answer_expansion_mode": True,
                "voice_playback_enabled": False,
            },
        )
        assert second_limited.status_code == 429, second_limited.text
    finally:
        app_module.RATE_LIMIT_PER_MINUTE = original_rate_limit
        app_module.REQUEST_LOG.clear()

    print("V2 FastAPI smoke test passed")
    print(f"phase: {session['phase']}")
    print(f"messages: {len(session['messages'])}")


if __name__ == "__main__":
    main()
