from __future__ import annotations

import base64
from collections import Counter
from difflib import SequenceMatcher
import io
import os
from pathlib import Path
import random
import re
import sys
import uuid

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from question_bank import (  # noqa: E402
    EXTRA_CUE_CARDS,
    PART1_SECONDARY_TOPICS,
    PART1_STUDY_QUESTIONS,
    PART1_WORK_QUESTIONS,
)

from .schemas import AnswerStats, CandidateAnswer, ChatMessage, ExamSession


PART1_FIRST_QUESTION = "Do you work, or are you a student?"
FIRST_MESSAGE = (
    "**Part 1 - Introduction and Interview**\n\n"
    "Good afternoon. My name is Victoria, and I will be your examiner today. "
    "Could you tell me your full name, please?"
)

MOCK_PART3_QUESTION_COUNT = 4
PRACTICE_PART3_QUESTION_COUNT = 6
PART3_MAX_QUESTION_COUNT = 6
LONG_ANSWER_WORD_THRESHOLD = 45

PART1_GENERAL_FOLLOWUPS = [
    "What do you usually do during a typical weekday?",
    "What part of your daily routine do you enjoy most?",
]

APP_BASE_CUE_CARDS = [
    {
        "title": "an interesting building",
        "prompt": (
            "Describe a building that you think is interesting.\n\n"
            "You should say:\n"
            "- what the building is\n"
            "- where it is\n"
            "- what it looks like\n"
            "- and explain why you find it interesting"
        ),
        "follow_up": "Would you like to visit this building again? Why or why not?",
        "part3": [
            "What makes a building attractive to the public?",
            "Should architects give more importance to beauty or function?",
            "Why is it important to preserve some old buildings?",
            "How might public buildings change in the future?",
        ],
    },
    {
        "title": "a useful skill",
        "prompt": (
            "Describe a useful skill that you learned.\n\n"
            "You should say:\n"
            "- what the skill is\n"
            "- when and where you learned it\n"
            "- how you learned it\n"
            "- and explain why this skill is useful to you"
        ),
        "follow_up": "Would you like to become even better at this skill?",
        "part3": [
            "What skills are most important for young people today?",
            "Is it easier to learn practical skills online or face to face?",
            "Should schools spend more time teaching practical skills?",
            "How will the skills needed for work change in the future?",
        ],
    },
    {
        "title": "an inspiring person",
        "prompt": (
            "Describe a person who has inspired you.\n\n"
            "You should say:\n"
            "- who this person is\n"
            "- how you know this person\n"
            "- what qualities this person has\n"
            "- and explain how this person inspired you"
        ),
        "follow_up": "Would you like to be more like this person in the future?",
        "part3": [
            "What qualities make someone a good role model?",
            "Are famous people always suitable role models for young people?",
            "How can teachers motivate their students?",
            "Do people become less easily influenced as they get older?",
        ],
    },
]

ALL_CUE_CARDS = APP_BASE_CUE_CARDS + list(EXTRA_CUE_CARDS)
EXPECTED_CUE_CARD_COUNT = 73


def get_secret(name: str, default: str | None = None) -> str | None:
    return os.getenv(name) or os.getenv(f"STREAMLIT_{name}") or default


API_KEY = get_secret("API_KEY")
BASE_URL = get_secret("BASE_URL", "https://api.gptsapi.net/v1")
MODEL = get_secret("MODEL", "gpt-5.4-mini")
TRANSCRIPTION_MODEL = get_secret("TRANSCRIPTION_MODEL", "whisper-1")


def get_question_bank_summary() -> dict[str, int]:
    part1_secondary_question_count = sum(
        len(topic["questions"]) for topic in PART1_SECONDARY_TOPICS
    )
    part1_identity_followup_count = len(PART1_STUDY_QUESTIONS) + len(PART1_WORK_QUESTIONS)
    return {
        "part1_topics": len(PART1_SECONDARY_TOPICS) + 2,
        "part1_secondary_topics": len(PART1_SECONDARY_TOPICS),
        "part1_total_questions": part1_secondary_question_count + part1_identity_followup_count,
        "part1_secondary_questions": part1_secondary_question_count,
        "part1_identity_followup_questions": part1_identity_followup_count,
        "part2_base_cards": len(APP_BASE_CUE_CARDS),
        "part2_extra_cards": len(EXTRA_CUE_CARDS),
        "part2_total_cards": len(ALL_CUE_CARDS),
        "part2_expected_cards": EXPECTED_CUE_CARD_COUNT,
        "part3_reference_questions": sum(len(card.get("part3", [])) for card in ALL_CUE_CARDS),
    }


def get_client():
    if not API_KEY:
        raise RuntimeError("Missing API_KEY environment variable.")
    from openai import OpenAI

    return OpenAI(api_key=API_KEY, base_url=BASE_URL)


def call_model(messages: list[dict[str, str]]) -> str:
    response = get_client().chat.completions.create(model=MODEL, messages=messages)
    return response.choices[0].message.content.strip()


def clean_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "NONE":
        return None
    return cleaned


def extract_feedback_field(text: str, label_pattern: str) -> str | None:
    pattern = rf"{label_pattern}\s*:\s*(.*?)(?=\n[A-Z_ ]+\s*:|\Z)"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return clean_none(match.group(1))


def normalize_spoken_text_for_similarity(text: str) -> str:
    text = text.lower()
    replacements = {
        "i'm": "i am",
        "i’m": "i am",
        "don't": "do not",
        "don’t": "do not",
        "can't": "cannot",
        "can’t": "cannot",
        "it's": "it is",
        "it’s": "it is",
        "that's": "that is",
        "that’s": "that is",
        "you're": "you are",
        "you’re": "you are",
        "i've": "i have",
        "i’ve": "i have",
        "i'd": "i would",
        "i’d": "i would",
        "i'll": "i will",
        "i’ll": "i will",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def should_show_upgraded_answer(
    original_answer: str,
    upgraded_answer: str | None,
    correction: str | None,
    expression_tip: str | None,
) -> bool:
    if not upgraded_answer:
        return False
    original = normalize_spoken_text_for_similarity(original_answer)
    upgraded = normalize_spoken_text_for_similarity(upgraded_answer)
    if not original or not upgraded:
        return False

    original_words = original.split()
    upgraded_words = upgraded.split()
    similarity = SequenceMatcher(None, original, upgraded).ratio()
    if original == upgraded or similarity >= 0.9:
        return False
    if not correction and not expression_tip:
        if len(upgraded_words) <= len(original_words) + 2 and similarity >= 0.78:
            return False
        if len(original_words) <= 5 and upgraded.startswith(original):
            return False
    return True


def coach_spoken_answer(
    question: str,
    answer: str,
    include_upgrade: bool,
) -> tuple[str | None, str | None, str | None]:
    spoken_words = re.findall(r"[A-Za-z']+", answer)
    if not spoken_words:
        return None, None, None

    answer_length = "LONG" if len(spoken_words) >= LONG_ANSWER_WORD_THRESHOLD else "SHORT"
    prompt = f"""
You are Victoria, an IELTS Speaking coach.

Return exactly three labelled lines:
CORRECTION: NONE
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: NONE

Rules:
- The answer is a speech-to-text transcript. Never correct capitalization,
  punctuation, spelling, obvious transcript mistakes, or proper-name casing.
- Correct only genuine spoken grammar, vocabulary choice, sentence structure,
  coherence, or fluency issues that would be heard in speech.
- If the answer is already natural and appropriate, return NONE for correction
  and UPGRADED_ANSWER.
- Only give an upgraded answer when ENABLE_UPGRADE is YES and the rewritten
  version is meaningfully more natural or better developed.
- Preserve the candidate's meaning. Do not invent a new personal story.
- Keep correction and expression tip to one short sentence each.

ENABLE_UPGRADE: {"YES" if include_upgrade else "NO"}
ANSWER_LENGTH: {answer_length}
Question: {question}
Answer: {answer}
"""
    try:
        result = call_model(
            [
                {
                    "role": "system",
                    "content": (
                        "You give concise IELTS spoken-language feedback. "
                        "Use the exact labels requested and no extra prose."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
    except Exception:
        return None, None, None

    correction = extract_feedback_field(result, "CORRECTION")
    expression_tip = extract_feedback_field(result, "EXPRESSION_TIP")
    upgraded_answer = extract_feedback_field(result, "UPGRADED[_ ]ANSWER")
    if expression_tip and correction and expression_tip.lower() == correction.lower():
        expression_tip = None
    if not should_show_upgraded_answer(answer, upgraded_answer, correction, expression_tip):
        upgraded_answer = None
    return correction, expression_tip, upgraded_answer


def extract_single_question(text: str) -> str | None:
    cleaned = re.sub(r"^\s*[-*\d.)]+\s*", "", text.strip())
    candidates = re.findall(r"[^?\n]+\?", cleaned)
    if not candidates:
        return None
    return re.sub(r"\s+", " ", candidates[0]).strip()


def fallback_part3_question(session: ExamSession) -> str:
    asked = {q.lower().strip() for q in session.part3_questions}
    pool = list(session.cue_card.get("part3", []))
    for question in pool:
        if question.lower().strip() not in asked:
            return question
    generic = [
        "Why do people's opinions on this topic often differ?",
        "What changes might happen in this area in the future?",
        "Do you think this issue affects young and older people differently?",
        "What are the advantages and disadvantages of this trend?",
    ]
    for question in generic:
        if question.lower().strip() not in asked:
            return question
    return "What is the most important thing people should consider about this issue?"


def generate_next_part3_question(session: ExamSession) -> str:
    latest = session.part3_history[-1] if session.part3_history else None
    reference_questions = "\n".join(f"- {q}" for q in session.cue_card.get("part3", [])[:8])
    history = "\n".join(
        f"Q: {item['question']}\nA: {item['answer']}" for item in session.part3_history[-3:]
    )
    prompt = f"""
You are choosing the next IELTS Speaking Part 3 question.

Part 2 cue card:
{session.cue_card.get("prompt", "")}

Candidate Part 2 answer summary:
{" ".join(session.part2_answers[-2:])}

Reference Part 3 question bank:
{reference_questions}

Recent Part 3 exchange:
{history or "No Part 3 answer yet."}

Task:
- Ask exactly ONE Part 3 question.
- It must be analytical, not personal.
- If the latest answer gives a concrete detail, visibly connect the next question to it.
- Do not repeat already asked questions.
- Return only the question.
"""
    try:
        question = extract_single_question(
            call_model(
                [
                    {
                        "role": "system",
                        "content": "You are a concise IELTS examiner. Return one question only.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
        )
    except Exception:
        question = None
    if not question or question.lower() in {q.lower() for q in session.part3_questions}:
        return fallback_part3_question(session)
    return question


def get_part3_question_count(session: ExamSession) -> int:
    if session.practice_mode:
        return min(PRACTICE_PART3_QUESTION_COUNT, PART3_MAX_QUESTION_COUNT)
    return min(MOCK_PART3_QUESTION_COUNT, PART3_MAX_QUESTION_COUNT)


def choose_part1_followups(session: ExamSession, answer: str) -> list[str]:
    normalized = answer.lower()
    if re.search(r"\b(student|study|studying|university|college|school)\b", normalized):
        personal_pool = PART1_STUDY_QUESTIONS
    elif re.search(r"\b(work|working|job|employed|employee)\b", normalized):
        personal_pool = PART1_WORK_QUESTIONS
    else:
        personal_pool = PART1_GENERAL_FOLLOWUPS
    personal_questions = random.sample(personal_pool, k=min(2, len(personal_pool)))
    secondary_questions = list(session.part1_secondary_questions)
    if secondary_questions:
        topic_name = session.part1_topic or "another topic"
        secondary_questions[0] = f"Let's talk about {topic_name}. {secondary_questions[0]}"
    return personal_questions + secondary_questions


def is_clarification_request(answer: str) -> bool:
    normalized = answer.lower()
    patterns = [
        r"\bi don't understand\b",
        r"\bi do not understand\b",
        r"\bwhat do you mean\b",
        r"\bcould you (repeat|rephrase|explain)\b",
        r"\bcan you (repeat|rephrase|explain)\b",
        r"\bplease (repeat|rephrase|explain)\b",
    ]
    return any(re.search(pattern, normalized) for pattern in patterns)


def rephrase_question(question: str) -> str:
    fallback = f"No problem. Let me ask it more simply: {question.strip()}"
    try:
        simplified = extract_single_question(
            call_model(
                [
                    {
                        "role": "system",
                        "content": "Rephrase the IELTS question in simpler natural English.",
                    },
                    {"role": "user", "content": question},
                ]
            )
        )
    except Exception:
        return fallback
    return f"No problem. Let me ask it more simply: {simplified}" if simplified else fallback


def build_reply(
    correction: str | None,
    expression_tip: str | None,
    upgraded_answer: str | None,
    next_content: str,
) -> str:
    sections = []
    if correction:
        sections.append(f"**Quick correction:** {correction}")
    if expression_tip:
        sections.append(f"**Better expression:** {expression_tip}")
    if upgraded_answer:
        sections.append(f"**A natural version of your answer:**\n\n> {upgraded_answer}")
    sections.append(next_content)
    return "\n\n".join(sections)


def start_session(
    practice_mode: bool = True,
    practice_type: str = "full",
    answer_expansion_mode: bool = True,
    voice_playback_enabled: bool = True,
) -> ExamSession:
    selected_topic = random.choice(PART1_SECONDARY_TOPICS)
    cue_card = random.choice(ALL_CUE_CARDS)
    session = ExamSession(
        session_id=str(uuid.uuid4()),
        messages=[ChatMessage(role="assistant", content=FIRST_MESSAGE, phase="identity")],
        current_question=FIRST_MESSAGE,
        practice_mode=practice_mode,
        practice_type=practice_type,
        answer_expansion_mode=answer_expansion_mode,
        voice_playback_enabled=voice_playback_enabled,
        part1_topic=selected_topic["name"],
        part1_secondary_questions=random.sample(
            selected_topic["questions"],
            k=min(3, len(selected_topic["questions"])),
        ),
        part3_target_count=PRACTICE_PART3_QUESTION_COUNT if practice_mode else MOCK_PART3_QUESTION_COUNT,
        cue_card=cue_card,
    )
    if practice_type == "part2":
        session.phase = "part2_long"
        session.messages = [
            ChatMessage(
                role="assistant",
                content=(
                    "**Part 2 - Long Turn**\n\n"
                    f"{cue_card['prompt']}\n\n"
                    "You have one minute to prepare. Then speak for one to two minutes."
                ),
                phase="part2_long",
            )
        ]
        session.current_question = cue_card["prompt"]
    elif practice_type == "part3":
        first_part3 = fallback_part3_question(session)
        session.phase = "part3"
        session.part3_questions = [first_part3]
        session.part3_index = 0
        session.messages = [
            ChatMessage(
                role="assistant",
                content=(
                    "**Part 3 - Discussion Practice**\n\n"
                    f"Topic: {cue_card.get('title', 'IELTS discussion')}\n\n"
                    f"{first_part3}"
                ),
                phase="part3",
            )
        ]
        session.current_question = first_part3
    return session


def save_answer_stats(
    session: ExamSession,
    answer: str,
    source: str,
    duration: float | None,
    phase: str,
) -> None:
    word_count = len(re.findall(r"[A-Za-z']+", answer))
    words_per_minute = None
    if duration and duration >= 2:
        words_per_minute = round(word_count / (duration / 60), 1)
    session.answer_stats.append(
        AnswerStats(
            phase=phase,
            source=source,
            duration=duration,
            word_count=word_count,
            words_per_minute=words_per_minute,
        )
    )
    session.candidate_answers.append(
        CandidateAnswer(
            phase=phase,
            question=session.current_question,
            answer=answer,
            source=source,
            duration=duration,
        )
    )


def handle_identity_phase(session: ExamSession) -> tuple[str, bool]:
    session.phase = "part1"
    session.part1_index = 0
    return PART1_FIRST_QUESTION, False


def handle_part1_phase(session: ExamSession, answer: str) -> tuple[str, bool]:
    if not session.part1_queue:
        session.part1_queue = choose_part1_followups(session, answer)
    index = session.part1_index
    if index < len(session.part1_queue):
        next_content = session.part1_queue[index]
        session.part1_index += 1
        return next_content, False

    if session.practice_type == "part1":
        session.phase = "complete"
        session.test_active = False
        return "Thank you. That is the end of Part 1 practice. Tap **Score** to view your report.", False

    session.phase = "part2_long"
    session.part2_words = 0
    session.part2_duration = 0.0
    session.part2_audio_used = False
    session.part2_extension_used = False
    session.part2_answers = []
    session.part3_questions = []
    session.part3_history = []
    card = session.cue_card
    next_content = (
        "**Part 2 - Long Turn**\n\n"
        f"{card['prompt']}\n\n"
        "You have one minute to prepare. Then speak for one to two minutes."
    )
    return next_content, True


def handle_part2_long_phase(
    session: ExamSession,
    answer: str,
    duration: float | None,
) -> tuple[str, bool]:
    session.part2_answers.append(answer)
    session.part2_words += len(re.findall(r"[A-Za-z']+", answer))
    if duration:
        session.part2_duration += duration
        session.part2_audio_used = True
    needs_more = (
        session.part2_duration < 50
        if session.part2_audio_used
        else session.part2_words < 80
    )
    if needs_more and not session.part2_extension_used:
        session.part2_extension_used = True
        return "Please continue - you still have time. Add more detail or give an example.", False

    session.phase = "part2_followup"
    return session.cue_card["follow_up"], False


def handle_part2_followup_phase(session: ExamSession, answer: str) -> tuple[str, bool]:
    session.part2_answers.append(answer)
    if session.practice_type == "part2":
        session.phase = "complete"
        session.test_active = False
        return "Thank you. That is the end of Part 2 practice. Tap **Score** to view your report.", False

    session.part3_target_count = get_part3_question_count(session)
    session.part3_questions = []
    session.part3_history = []
    first_part3 = generate_next_part3_question(session)
    session.part3_questions.append(first_part3)
    session.phase = "part3"
    session.part3_index = 0
    return f"**Part 3 - Discussion**\n\n{first_part3}", False


def handle_part3_phase(
    session: ExamSession,
    answer: str,
    previous_question: str,
) -> tuple[str, bool]:
    current_question = session.part3_questions[-1] if session.part3_questions else previous_question
    if is_clarification_request(answer):
        return rephrase_question(current_question), False

    session.part3_history.append({"question": current_question, "answer": answer})
    session.part3_index = len(session.part3_history)
    if session.part3_index < session.part3_target_count:
        next_question = generate_next_part3_question(session)
        session.part3_questions.append(next_question)
        return next_question, False

    session.phase = "complete"
    session.test_active = False
    return (
        "Thank you. That is the end of the speaking test. "
        "Tap **Get Score** to view your report."
    ), False


def process_answer(
    session: ExamSession,
    answer: str,
    source: str = "text",
    duration: float | None = None,
) -> tuple[ExamSession, ChatMessage, str, bool]:
    phase = session.phase
    previous_question = session.current_question
    save_answer_stats(session, answer, source, duration, phase)
    session.messages.append(ChatMessage(role="user", content=answer, phase=phase))

    correction = None
    expression_tip = None
    upgraded_answer = None
    include_upgrade = (
        session.practice_mode
        and session.answer_expansion_mode
        and phase in {"part1", "part2_followup", "part3"}
    )
    if session.practice_mode and phase != "identity":
        correction, expression_tip, upgraded_answer = coach_spoken_answer(
            previous_question,
            answer,
            include_upgrade,
        )

    if phase == "identity":
        next_content, start_prep_timer = handle_identity_phase(session)

    elif phase == "part1":
        next_content, start_prep_timer = handle_part1_phase(session, answer)

    elif phase == "part2_long":
        next_content, start_prep_timer = handle_part2_long_phase(session, answer, duration)

    elif phase == "part2_followup":
        next_content, start_prep_timer = handle_part2_followup_phase(session, answer)

    elif phase == "part3":
        next_content, start_prep_timer = handle_part3_phase(session, answer, previous_question)
    else:
        next_content = "The test is complete. Tap **Get Score**."
        start_prep_timer = False

    if session.phase == "part2_long" and next_content.startswith("Please continue"):
        session.current_question = session.cue_card["prompt"]
    elif session.phase == "part3" and session.part3_questions:
        session.current_question = session.part3_questions[-1]
    else:
        session.current_question = next_content

    reply = build_reply(correction, expression_tip, upgraded_answer, next_content)
    assistant_message = ChatMessage(role="assistant", content=reply, phase=session.phase)
    session.messages.append(assistant_message)
    return session, assistant_message, next_content, start_prep_timer


def audio_filename_from_mime(mime_type: str) -> str:
    if "wav" in mime_type:
        return "ielts_answer.wav"
    if "mp4" in mime_type or "m4a" in mime_type:
        return "ielts_answer.m4a"
    if "mpeg" in mime_type or "mp3" in mime_type:
        return "ielts_answer.mp3"
    return "ielts_answer.webm"


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = audio_filename_from_mime(mime_type)
    transcription = get_client().audio.transcriptions.create(
        model=TRANSCRIPTION_MODEL,
        file=audio_file,
        language="en",
    )
    text = getattr(transcription, "text", None)
    return text.strip() if text else ""


def synthesize_speech(text: str) -> bytes:
    from gtts import gTTS

    clean_text = text.replace("*", "").replace("#", "").replace("- ", "")
    audio_buffer = io.BytesIO()
    gTTS(text=clean_text, lang="en", tld="co.uk").write_to_fp(audio_buffer)
    return audio_buffer.getvalue()


def export_candidate_answer_log(session: ExamSession) -> str:
    lines = []
    for index, item in enumerate(session.candidate_answers, start=1):
        timing = f", duration={item.duration:.1f}s" if item.duration else ""
        lines.append(
            f"{index}. [{item.phase}] Q: {item.question}\n"
            f"   A ({item.source}{timing}): {item.answer}"
        )
    return "\n".join(lines) or "No candidate answers recorded."


def build_session_learning_summary(session: ExamSession) -> str:
    answers = [item for item in session.candidate_answers if item.phase != "identity"]
    stats = [item for item in session.answer_stats if item.phase != "identity"]
    phases = {item.phase for item in answers}
    answer_words = [
        re.findall(r"[A-Za-z']+", item.answer.lower())
        for item in answers
    ]
    flat_words = [word for words in answer_words for word in words]
    total_words = len(flat_words)
    average_words = round(total_words / len(answers), 1) if answers else 0
    short_answers = sum(1 for words in answer_words if len(words) < 12)
    wpm_values = [item.words_per_minute for item in stats if item.words_per_minute]
    average_wpm = round(sum(wpm_values) / len(wpm_values), 1) if wpm_values else None

    vague_terms = {
        "good",
        "nice",
        "interesting",
        "beautiful",
        "thing",
        "things",
        "stuff",
        "very",
        "really",
        "many",
    }
    vague_counter = Counter(word for word in flat_words if word in vague_terms)
    repeated_vague = [word for word, count in vague_counter.most_common(5) if count >= 2]

    grammar_watchlist = []
    transcript = "\n".join(item.answer.lower() for item in answers)
    grammar_patterns = [
        (r"\bi am student\b|\bi'm student\b", "Use articles with singular countable nouns, e.g. 'I'm a student.'"),
        (r"\bhave a work\b|\ba work\b", "Use 'a job' for one position; 'work' is usually uncountable."),
        (r"\bmore better\b", "Avoid double comparatives such as 'more better'."),
        (r"\bpeople is\b|\bthey is\b", "Watch subject-verb agreement with plural subjects."),
        (r"\bmany thing\b|\bmany stuffs\b", "Use plural countable forms naturally, e.g. 'many things'."),
    ]
    for pattern, note in grammar_patterns:
        if re.search(pattern, transcript) and note not in grammar_watchlist:
            grammar_watchlist.append(note)

    weaknesses = []
    if answers and short_answers / len(answers) >= 0.4:
        weaknesses.append(
            "Answer development: many answers are under 12 words, so they need one reason, example, or contrast."
        )
    if repeated_vague:
        weaknesses.append(
            "Lexical precision: repeated broad words such as "
            + ", ".join(repeated_vague)
            + " should be replaced with more specific topic vocabulary."
        )
    if "part2_long" in phases and session.part2_audio_used and session.part2_duration < 60:
        weaknesses.append("Part 2 stamina: the long turn is still short; aim for 90-120 seconds.")
    elif "part2_long" not in phases:
        weaknesses.append("Part 2 evidence is missing, so long-turn fluency is not fully tested yet.")
    if "part3" not in phases:
        weaknesses.append("Part 3 reasoning is under-tested; practise opinion + reason + example answers.")
    if average_wpm and average_wpm < 90:
        weaknesses.append(f"Fluency pace: average speed is about {average_wpm} WPM, which may sound hesitant.")
    elif average_wpm and average_wpm > 180:
        weaknesses.append(f"Fluency pace: average speed is about {average_wpm} WPM, which may sound rushed.")
    if grammar_watchlist:
        weaknesses.append("Grammar watchlist: " + grammar_watchlist[0])
    if not weaknesses:
        weaknesses.append(
            "No dominant pattern was detected from the saved answers; keep focusing on fuller, more specific responses."
        )

    if answers and short_answers / len(answers) >= 0.4:
        next_focus = "Extend short answers with a clear reason and one concrete example."
    elif repeated_vague:
        next_focus = "Replace vague adjectives with precise topic vocabulary and short examples."
    elif "part3" not in phases:
        next_focus = "Complete a Part 3 set and practise abstract comparisons."
    elif "part2_long" in phases and session.part2_duration and session.part2_duration < 60:
        next_focus = "Build one Part 2 answer to at least 90 seconds without stopping."
    else:
        next_focus = "Maintain the full test flow and collect more audio-timed answers."

    evidence = (
        f"{len(answers)} scored answers, {total_words} words, "
        f"average {average_words} words per answer"
    )
    if average_wpm:
        evidence += f", average {average_wpm} WPM"

    return "\n\n".join(
        [
            "## Session learning summary",
            f"**Evidence used:** {evidence}.",
            "**Recurring weaknesses:**\n" + "\n".join(f"- {item}" for item in weaknesses[:4]),
            "**Grammar watchlist:**\n"
            + (
                "\n".join(f"- {item}" for item in grammar_watchlist[:3])
                if grammar_watchlist
                else "- No repeated grammar pattern was confidently detected."
            ),
            f"**Next-session focus:** {next_focus}",
        ]
    )


def build_fallback_report(session: ExamSession) -> str:
    answers = [item for item in session.candidate_answers if item.phase != "identity"]
    stats = [item for item in session.answer_stats if item.phase != "identity"]
    total_words = sum(len(re.findall(r"[A-Za-z']+", item.answer)) for item in answers)
    average_words = round(total_words / len(answers), 1) if answers else 0
    phases = {item.phase for item in answers}
    wpm_values = [item.words_per_minute for item in stats if item.words_per_minute]
    average_wpm = round(sum(wpm_values) / len(wpm_values), 1) if wpm_values else None

    if not answers:
        band_range = "not enough evidence"
    elif {"part2_long", "part3"}.issubset(phases) and average_words >= 35:
        band_range = "around 6.0-6.5, pending human/model review"
    elif average_words >= 18:
        band_range = "around 5.5-6.0, pending human/model review"
    else:
        band_range = "around 5.0-5.5, pending human/model review"

    problems = []
    if average_words and average_words < 18:
        problems.append("Many answers are very short, so they leave little room to show fluency and range.")
    if "part2_long" not in phases:
        problems.append("There is not enough Part 2 evidence yet; the long-turn answer is essential for scoring.")
    elif session.part2_audio_used and session.part2_duration < 60:
        problems.append("The Part 2 long turn appears short; aim closer to 90-120 seconds in mock mode.")
    if "part3" not in phases:
        problems.append("There is not enough Part 3 evidence yet, so abstract discussion ability is under-tested.")
    if average_wpm and (average_wpm < 90 or average_wpm > 180):
        problems.append(f"The average speaking pace is about {average_wpm} WPM, which may need adjustment.")
    if not problems:
        problems.append("No single issue dominates the rule-based summary; review the transcript for repeated language patterns.")

    tasks = [
        "Give every Part 1 answer a direct answer plus one reason or example.",
        "Practise one complete Part 2 answer for 90-120 seconds before requesting a score.",
        "For Part 3, answer with a clear opinion, one reason, and one real-world example.",
    ]

    return "\n\n".join(
        [
            "## Final report (rule-based fallback)",
            "The AI scoring model was temporarily unavailable, so this report uses the saved raw answers and timing data only.",
            f"**Estimated band range:** {band_range}",
            f"**Evidence used:** {len(answers)} candidate answers, {total_words} spoken words, average answer length {average_words} words.",
            f"**Speaking pace:** {average_wpm} WPM." if average_wpm else "**Speaking pace:** not enough audio timing evidence.",
            "**Main issues noticed:**\n" + "\n".join(f"- {problem}" for problem in problems[:3]),
            "**Next-session practice tasks:**\n" + "\n".join(f"{index}. {task}" for index, task in enumerate(tasks, start=1)),
            build_session_learning_summary(session),
        ]
    )


def build_report(session: ExamSession) -> str:
    prompt = f"""
Create a clear IELTS Speaking practice report based only on the candidate answers below.

Include:
1. Estimated overall band score.
2. Separate comments for Fluency and Coherence, Lexical Resource, and Grammar.
3. Three recurring spoken-language problems.
4. Three corrected examples based on the candidate's meaning.
5. Exactly three next-session practice tasks.

Do not include a generic seven-day plan.
Do not assess pronunciation unless audio timing alone supports a cautious observation.

Raw answer log:
{export_candidate_answer_log(session)}
"""
    try:
        model_report = call_model(
            [
                {
                    "role": "system",
                    "content": "You are a strict but helpful IELTS Speaking examiner.",
                },
                {"role": "user", "content": prompt},
            ]
        )
        return f"{model_report.strip()}\n\n---\n\n{build_session_learning_summary(session)}"
    except Exception:
        return build_fallback_report(session)
