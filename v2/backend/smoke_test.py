from __future__ import annotations

from fastapi.testclient import TestClient

from v2.backend.app import app


def main() -> None:
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200, health.text

    question_bank = client.get("/api/question-bank")
    assert question_bank.status_code == 200, question_bank.text
    bank = question_bank.json()
    assert bank["part2_total_cards"] == 73, bank
    assert bank["part2_total_cards"] == bank["part2_expected_cards"], bank

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

    print("V2 FastAPI smoke test passed")
    print(f"phase: {session['phase']}")
    print(f"messages: {len(session['messages'])}")


if __name__ == "__main__":
    main()
