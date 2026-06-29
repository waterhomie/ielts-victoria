from __future__ import annotations

from fastapi.testclient import TestClient

from v2.backend.app import app
from v2.backend.engine import build_fallback_report
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

    start = client.post(
        "/api/sessions",
        json={
            "practice_mode": True,
            "answer_expansion_mode": True,
            "voice_playback_enabled": False,
        },
    )
    assert start.status_code == 200, start.text
    session = start.json()["session"]
    assert session["phase"] == "identity"

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

    report = client.post("/api/report", json={"session": session})
    assert report.status_code == 200, report.text
    report_text = report.json()["report"]
    assert "Report generation failed" not in report_text, report_text
    assert len(report_text) > 80, report_text

    fallback_text = build_fallback_report(ExamSession.model_validate(session))
    assert "rule-based fallback" in fallback_text, fallback_text
    assert "Next-session practice tasks" in fallback_text, fallback_text

    print("V2 FastAPI smoke test passed")
    print(f"phase: {session['phase']}")
    print(f"messages: {len(session['messages'])}")


if __name__ == "__main__":
    main()
