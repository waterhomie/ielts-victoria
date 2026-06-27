import io
import random
import re
import time
import wave

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from openai import OpenAI

from question_bank import (
    EXTRA_CUE_CARDS,
    PART1_SECONDARY_TOPICS,
    PART1_STUDY_QUESTIONS,
    PART1_WORK_QUESTIONS,
)


# --- WEB APP SETUP ---
st.set_page_config(
    page_title="IELTS Victoria Pro",
    page_icon="🎓",
    layout="centered",
)


# --- CONFIGURATION ---
def get_secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


API_KEY = get_secret("API_KEY")
BASE_URL = get_secret("BASE_URL", "https://api.gptsapi.net/v1")
MODEL = get_secret("MODEL", "gpt-5.4-mini")
TRANSCRIPTION_MODEL = get_secret("TRANSCRIPTION_MODEL", "whisper-1")
MOCK_PART3_QUESTION_COUNT = 4
PRACTICE_PART3_QUESTION_COUNT = 6

if not API_KEY:
    st.error(
        "Missing API_KEY. Please add API_KEY in Streamlit Cloud → App settings → Secrets."
    )
    st.stop()

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# --- TEST CONTENT ---
PART1_FIRST_QUESTION = "Do you work, or are you a student?"

PART1_STUDENT_FOLLOWUPS = PART1_STUDY_QUESTIONS
PART1_WORK_FOLLOWUPS = PART1_WORK_QUESTIONS

PART1_GENERAL_FOLLOWUPS = [
    "What do you usually do during a typical weekday?",
    "What part of your daily routine do you enjoy most?",
]

CUE_CARDS = [
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

CUE_CARDS.extend(EXTRA_CUE_CARDS)

FIRST_MESSAGE = (
    "**Part 1 - Introduction and Interview**\n\n"
    "Good afternoon. My name is Victoria, and I will be your examiner today. "
    "Could you tell me your full name, please?"
)

EXAM_CONTEXT = """
This is an IELTS Speaking practice test. User messages are speech-to-text transcripts.
Never treat capitalization, punctuation, or spelling as evidence of spoken ability.
The program controls the test stages. Do not infer the stage from the conversation.
"""

FEEDBACK_COACH_PROMPT = """
You are a careful spoken-English feedback coach for an IELTS practice app.
The candidate's answer is a speech-to-text transcript, not written English.
Use the examiner's question to understand the intended meaning, tense, emotion,
and context behind the answer.

Return exactly three labelled lines in this order:
CORRECTION: NONE
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: NONE

Replace NONE only when the relevant rules below require content.

Correction rules:
- Silently ask: "Could this error actually be heard?"
- If it could not be heard, use CORRECTION: NONE.
- Ignore capitalization, punctuation, spelling, formatting, proper-name capitalization,
  and obvious speech-recognition mistakes.
- Do not rewrite an answer merely to make it more elegant or complete.
- A short answer or sentence fragment that naturally answers the examiner's question
  is not automatically a grammar error.
- Correct only genuine audible problems in grammar, word choice, sentence structure,
  or spoken fluency.
- The corrected version must be natural English, not a mechanical word-for-word repair.
- Preserve the candidate's intended meaning and use the tense required by the question.
- Do not explain grammar rules and do not list several quoted fragments.
- For a long answer, rewrite only one coherent sentence containing the two
  highest-impact improvements.

Expression-tip rules:
- This is for meaning and idiomatic word choice, not spelling.
- Use EXPRESSION_TIP only when the candidate's word is too vague, unnatural,
  misleading, or too literal for the meaning they probably want to express.
- Help the candidate find the English phrase that better matches the same context
  and emotion. For example, if "sad" is being used to mean being misunderstood
  after doing something kind, suggest "felt wronged", "felt misunderstood", or
  "felt unfairly treated".
- Do not give an expression tip if the answer is already natural enough.
- Do not correct capitalization, punctuation, proper-name capitalization, or
  speech-to-text spelling noise through EXPRESSION_TIP.
- Keep EXPRESSION_TIP to one short sentence.

Personalized answer-upgrade rules:
- The user message will contain ENABLE_UPGRADE: YES or NO.
- If it is NO, use UPGRADED_ANSWER: NONE.
- If it is YES, produce a natural first-person answer of two or three sentences,
  no more than 60 words.
- Preserve the candidate's own central idea, emotion, and personal viewpoint.
- Develop that idea with a relevant reason, detail, consequence, comparison, or
  simple example. Do not replace it with a different opinion.
- Do not invent specific names, places, dates, achievements, or life experiences.
- Make the answer sound like attainable IELTS Band 6.5-7 English, not a memorized essay.
- The upgraded answer must already incorporate any genuine correction and any
  better expression suggested in EXPRESSION_TIP.

Example 1:
ENABLE_UPGRADE: YES
Question: "Do you enjoy your studies?"
Answer: "yes i do"
CORRECTION: NONE
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: Yes, I do. I enjoy learning how buildings are designed because it combines creativity with practical problem-solving.

Example 2:
ENABLE_UPGRADE: YES
Question: "What do you enjoy most about your studies?"
Answer: "i prefer study design because it is creative"
CORRECTION: I prefer studying design because it is creative.
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: I prefer studying design because it allows me to be creative. I particularly enjoy turning an initial idea into something practical and visually interesting.

Example 3:
ENABLE_UPGRADE: NO
Question: "Has your hometown changed much?"
Answer: "yes it become more quiet because of the youth loss"
CORRECTION: Yes, it has become quieter because many young people have moved away.
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: NONE

Example 4:
ENABLE_UPGRADE: YES
Question: "What subject do you study?"
Answer: "achitecture"
CORRECTION: NONE
EXPRESSION_TIP: NONE
UPGRADED_ANSWER: I study architecture. I chose this subject because I am interested in both creative design and the way buildings affect people's daily lives.

Example 5:
ENABLE_UPGRADE: YES
Question: "How did you feel when people misunderstood you?"
Answer: "i was very sad because i did a good thing but they thought i was wrong"
CORRECTION: NONE
EXPRESSION_TIP: Instead of "sad", "I felt misunderstood and unfairly treated" matches this situation more precisely.
UPGRADED_ANSWER: I felt misunderstood and unfairly treated because I had tried to do something kind, but people interpreted it in the wrong way. It was discouraging because my intention was completely different from how it was seen.
"""


def build_part3_adaptive_prompt(question_count):
    return f"""
You are an IELTS Speaking examiner preparing exactly {question_count} Part 3 discussion questions.

Use both sources:
1. The recall-question-bank questions supplied for this Part 2 topic.
2. The candidate's own Part 2 answer and short follow-up answer.

Rules:
- Keep the questions clearly connected to the recall-question-bank topic.
- In mock-test mode, this should feel like a realistic 4-5 minute Part 3 discussion.
- In practice mode, this may be slightly more intensive for training.
- The earlier questions should closely reflect useful angles from the question bank.
- At least one later question should extend an idea actually mentioned by the candidate.
- Turn personal details into broader analytical discussion about people, society, causes,
  comparisons, advantages and disadvantages, rules, or future change.
- Do not merely ask the candidate to repeat or add details to the Part 2 story.
- Do not assume the candidate said something that is absent from the transcript.
- Move from relatively accessible discussion to more abstract critical thinking.
- Return exactly {question_count} numbered, single-sentence questions and no other text.
"""


def get_part3_question_count():
    if st.session_state.get("practice_mode", True):
        return PRACTICE_PART3_QUESTION_COUNT
    return MOCK_PART3_QUESTION_COUNT


st.markdown(
    """
    <style>
    .stChatFloatingInputContainer {padding-bottom: 20px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎓 Examiner Victoria (Pro)")
st.caption("IELTS Speaking Practice with reliable stage control and feedback")


# --- MODEL AND AUDIO HELPERS ---
def call_model(messages):
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


def generate_adaptive_part3_questions(card, candidate_part2_answers, question_count):
    reference_questions = card.get("part3") or []
    fallback = list(reference_questions[:question_count])
    if len(fallback) < question_count:
        fallback.extend(
            [
                "Why might people have different opinions about this topic?",
                "How has this aspect of life changed in recent years?",
                "Are younger and older people likely to think differently about it?",
                "How might this topic develop in the future?",
                "What could individuals or governments do to improve this situation?",
            ][: question_count - len(fallback)]
        )

    reference_text = "\n".join(f"- {question}" for question in reference_questions)
    candidate_text = "\n".join(candidate_part2_answers).strip()
    if not candidate_text:
        candidate_text = "No usable candidate transcript was available."

    try:
        result = call_model(
            [
                {"role": "system", "content": build_part3_adaptive_prompt(question_count)},
                {
                    "role": "user",
                    "content": (
                        f"PART 2 TOPIC:\n{card['prompt']}\n\n"
                        f"REFERENCE PART 3 QUESTIONS:\n{reference_text}\n\n"
                        f"CANDIDATE'S PART 2 RESPONSES:\n{candidate_text}"
                    ),
                },
            ]
        )
    except Exception:
        return fallback

    questions = []
    for line in result.splitlines():
        cleaned = re.sub(r"^\s*(?:\d+[.)：:]|[-*])\s*", "", line).strip()
        if cleaned.endswith("?") and cleaned not in questions:
            questions.append(cleaned)

    if len(questions) < question_count:
        for question in fallback:
            if question not in questions:
                questions.append(question)
            if len(questions) == question_count:
                break

    return questions[:question_count]


def extract_feedback_field(model_output, label_pattern):
    match = re.search(
        rf"(?ims)^\s*{label_pattern}:\s*(.*?)(?=^\s*(?:CORRECTION|EXPRESSION_TIP|UPGRADED[_ ]ANSWER):|\Z)",
        model_output,
    )
    if not match:
        return None

    value = match.group(1).strip()
    value = re.sub(r"^```(?:\w+)?\s*|\s*```$", "", value).strip()
    if not value or value.upper() == "NONE":
        return None
    return value


def coach_spoken_answer(question, answer, include_upgrade):
    spoken_words = re.findall(r"[A-Za-z']+", answer)
    if not spoken_words:
        return None, None, None

    result = call_model(
        [
            {"role": "system", "content": FEEDBACK_COACH_PROMPT},
            {
                "role": "user",
                "content": (
                    f"ENABLE_UPGRADE: {'YES' if include_upgrade else 'NO'}\n\n"
                    f"EXAMINER QUESTION:\n{question}\n\n"
                    f"CANDIDATE ANSWER:\n{answer}"
                ),
            },
        ]
    )

    correction = extract_feedback_field(result, "CORRECTION")
    expression_tip = extract_feedback_field(result, "EXPRESSION_TIP")
    upgraded_answer = extract_feedback_field(result, "UPGRADED[_ ]ANSWER")

    if expression_tip and correction and expression_tip.lower() == correction.lower():
        expression_tip = None

    # Safe default: never display unstructured model output.
    return correction, expression_tip, upgraded_answer


def speak_text(text):
    clean_text = (
        text.replace("*", "")
        .replace("#", "")
        .replace("- ", "")
    )
    audio_buffer = io.BytesIO()
    gTTS(text=clean_text, lang="en", tld="co.uk").write_to_fp(audio_buffer)
    st.audio(audio_buffer.getvalue(), format="audio/mp3", autoplay=True)


def get_wav_duration(audio_bytes):
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as audio_file:
            frame_rate = audio_file.getframerate()
            if not frame_rate:
                return None
            return audio_file.getnframes() / float(frame_rate)
    except (wave.Error, EOFError):
        return None


def transcribe_audio(audio_bytes):
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "ielts_answer.wav"
    transcription = client.audio.transcriptions.create(
        model=TRANSCRIPTION_MODEL,
        file=audio_file,
        language="en",
    )
    text = getattr(transcription, "text", None)
    if not text and isinstance(transcription, dict):
        text = transcription.get("text")
    if not text:
        raise ValueError("The transcription service returned no text.")
    return text.strip()


def save_answer_stats(text, source, duration, phase):
    word_count = len(re.findall(r"[A-Za-z']+", text))
    words_per_minute = None
    if duration and duration >= 2:
        words_per_minute = round(word_count / (duration / 60))

    st.session_state.answer_stats.append(
        {
            "phase": phase,
            "source": source,
            "duration": round(duration, 1) if duration else None,
            "word_count": word_count,
            "wpm": words_per_minute,
        }
    )


def audio_stats_summary():
    recorded = [
        item
        for item in st.session_state.answer_stats
        if item["source"] == "audio" and item["duration"]
    ]
    if not recorded:
        return "No recorded-audio timing data was available."

    total_seconds = round(sum(item["duration"] for item in recorded), 1)
    total_words = sum(item["word_count"] for item in recorded)
    average_wpm = round(total_words / (total_seconds / 60)) if total_seconds else 0
    return (
        f"Recorded answers: {len(recorded)}; total speaking time: {total_seconds} seconds; "
        f"total transcribed words: {total_words}; average speaking rate: {average_wpm} WPM."
    )


def export_transcript():
    lines = ["IELTS Victoria Pro - Practice Transcript", ""]
    for message in st.session_state.messages:
        if message["role"] == "system":
            continue
        speaker = "Victoria" if message["role"] == "assistant" else "Candidate"
        lines.append(f"{speaker}: {message['content']}")
        lines.append("")
    lines.append("Audio statistics:")
    lines.append(audio_stats_summary())
    return "\n".join(lines)


def record_candidate_answer(phase, question, answer, source, duration):
    word_count = len(re.findall(r"[A-Za-z']+", answer))
    st.session_state.candidate_answers.append(
        {
            "phase": phase,
            "question": question,
            "answer": answer,
            "source": source,
            "duration": round(duration, 1) if duration else None,
            "word_count": word_count,
        }
    )


def export_candidate_answer_log():
    if not st.session_state.candidate_answers:
        return "No candidate answers were submitted."

    lines = ["Raw candidate answers only", ""]
    for index, item in enumerate(st.session_state.candidate_answers, start=1):
        lines.append(f"{index}. Stage: {item['phase']}")
        lines.append(f"Question: {item['question']}")
        lines.append(f"Candidate answer: {item['answer']}")
        lines.append(
            f"Input source: {item['source']}; word count: {item['word_count']}; "
            f"recorded duration: {item['duration'] if item['duration'] else 'N/A'} seconds"
        )
        lines.append("")
    return "\n".join(lines)


def render_countdown(end_time, label):
    remaining = max(0, int(end_time - time.time()))
    components.html(
        f"""
        <div style="font-family: sans-serif; padding: 12px; border: 1px solid #ddd;
                    border-radius: 8px; text-align: center;">
          <strong>{label}</strong>
          <div id="timer" style="font-size: 28px; margin-top: 6px;"></div>
        </div>
        <script>
          let remaining = {remaining};
          const timer = document.getElementById("timer");
          function renderTimer() {{
            if (remaining <= 0) {{
              timer.textContent = "Time is up";
              return false;
            }}
            const minutes = Math.floor(remaining / 60);
            const seconds = String(remaining % 60).padStart(2, "0");
            timer.textContent = `${{minutes}}:${{seconds}}`;
            remaining -= 1;
            return true;
          }}
          renderTimer();
          const timerId = setInterval(() => {{
            if (!renderTimer()) clearInterval(timerId);
          }}, 1000);
        </script>
        """,
        height=90,
    )


def reset_test():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


def choose_part1_followups(answer):
    normalized = answer.lower()
    if re.search(r"\b(student|study|studying|university|college|school)\b", normalized):
        personal_pool = PART1_STUDENT_FOLLOWUPS
    elif re.search(r"\b(work|working|job|employed|employee)\b", normalized):
        personal_pool = PART1_WORK_FOLLOWUPS
    else:
        personal_pool = PART1_GENERAL_FOLLOWUPS

    personal_questions = random.sample(personal_pool, k=min(2, len(personal_pool)))
    return personal_questions + st.session_state.part1_secondary_questions


def build_reply(correction, expression_tip, upgraded_answer, next_content):
    sections = []
    if correction:
        sections.append(f"**Quick correction:** {correction}")
    if expression_tip:
        sections.append(f"**Better expression:** {expression_tip}")
    if upgraded_answer:
        sections.append(f"**A natural version of your answer:**\n\n> {upgraded_answer}")
    sections.append(next_content)
    return "\n\n".join(sections)


# --- RELIABLE PROGRAM-CONTROLLED TEST FLOW ---
def process_candidate_answer(answer, previous_question, answer_duration=None):
    phase = st.session_state.phase
    correction = None
    expression_tip = None
    upgraded_answer = None
    include_upgrade = (
        st.session_state.practice_mode
        and st.session_state.answer_expansion_mode
        and phase in {"part1", "part2_followup", "part3"}
    )
    if st.session_state.practice_mode and phase != "identity":
        correction, expression_tip, upgraded_answer = coach_spoken_answer(
            previous_question,
            answer,
            include_upgrade,
        )

    start_prep_timer = False

    if phase == "identity":
        st.session_state.phase = "part1"
        st.session_state.part1_index = 0
        next_content = PART1_FIRST_QUESTION

    elif phase == "part1":
        if not st.session_state.part1_queue:
            st.session_state.part1_queue = choose_part1_followups(answer)
        index = st.session_state.part1_index
        if index < len(st.session_state.part1_queue):
            next_content = st.session_state.part1_queue[index]
            st.session_state.part1_index += 1
        else:
            st.session_state.phase = "part2_long"
            st.session_state.part2_words = 0
            st.session_state.part2_duration = 0.0
            st.session_state.part2_audio_used = False
            st.session_state.part2_extension_used = False
            st.session_state.part2_answers = []
            st.session_state.part3_questions = []
            st.session_state.timer_end = time.time() + 60
            st.session_state.timer_label = "Part 2 preparation time"
            start_prep_timer = True
            card = st.session_state.cue_card
            next_content = (
                "**Part 2 - Long Turn**\n\n"
                f"{card['prompt']}\n\n"
                "You have one minute to prepare. Then speak for one to two minutes."
            )

    elif phase == "part2_long":
        st.session_state.part2_answers.append(answer)
        st.session_state.part2_words += len(re.findall(r"[A-Za-z']+", answer))
        if answer_duration:
            st.session_state.part2_duration += answer_duration
            st.session_state.part2_audio_used = True

        needs_more = (
            st.session_state.part2_duration < 50
            if st.session_state.part2_audio_used
            else st.session_state.part2_words < 80
        )
        if (
            needs_more
            and not st.session_state.part2_extension_used
        ):
            st.session_state.part2_extension_used = True
            next_content = (
                "Please continue - you still have time. Add more detail or give an example."
            )
        else:
            st.session_state.phase = "part2_followup"
            next_content = st.session_state.cue_card["follow_up"]

    elif phase == "part2_followup":
        st.session_state.part2_answers.append(answer)
        st.session_state.part3_target_count = get_part3_question_count()
        st.session_state.part3_questions = generate_adaptive_part3_questions(
            st.session_state.cue_card,
            st.session_state.part2_answers,
            st.session_state.part3_target_count,
        )
        st.session_state.phase = "part3"
        st.session_state.part3_index = 1
        next_content = (
            "**Part 3 - Discussion**\n\n"
            + st.session_state.part3_questions[0]
        )

    elif phase == "part3":
        index = st.session_state.part3_index
        questions = st.session_state.part3_questions
        if index < len(questions):
            next_content = questions[index]
            st.session_state.part3_index += 1
        else:
            st.session_state.phase = "complete"
            st.session_state.test_active = False
            next_content = (
                "Thank you. That is the end of the speaking test. "
                "Click **End Test & Get Score** to view your report."
            )

    else:
        next_content = "The test is complete. Click **End Test & Get Score**."

    if (
        st.session_state.phase == "part2_long"
        and next_content.startswith("Please continue")
    ):
        st.session_state.current_question = st.session_state.cue_card["prompt"]
    else:
        st.session_state.current_question = next_content

    return (
        build_reply(correction, expression_tip, upgraded_answer, next_content),
        start_prep_timer,
        next_content,
    )


# --- SESSION STATE ---
if "messages" not in st.session_state:
    selected_part1_topic = random.choice(PART1_SECONDARY_TOPICS)
    st.session_state.messages = [
        {"role": "system", "content": EXAM_CONTEXT},
        {"role": "assistant", "content": FIRST_MESSAGE},
    ]
    st.session_state.phase = "identity"
    st.session_state.part1_index = 0
    st.session_state.part1_queue = []
    st.session_state.part1_topic = selected_part1_topic["name"]
    st.session_state.part1_secondary_questions = random.sample(
        selected_part1_topic["questions"],
        k=min(3, len(selected_part1_topic["questions"])),
    )
    st.session_state.part3_index = 0
    st.session_state.part2_words = 0
    st.session_state.part2_duration = 0.0
    st.session_state.part2_audio_used = False
    st.session_state.part2_extension_used = False
    st.session_state.part2_answers = []
    st.session_state.part3_questions = []
    st.session_state.cue_card = random.choice(CUE_CARDS)
    st.session_state.current_question = FIRST_MESSAGE
    st.session_state.test_active = True
    st.session_state.practice_mode = True
    st.session_state.answer_expansion_mode = True
    st.session_state.speak_full_reply = False
    st.session_state.part3_target_count = PRACTICE_PART3_QUESTION_COUNT
    st.session_state.answer_stats = []
    st.session_state.candidate_answers = []
    st.session_state.audio_input_key = 0


# --- SIDEBAR TOOLS ---
with st.sidebar:
    st.header("Exam Tools")

    st.toggle(
        "Practice mode - correction & expression coaching",
        key="practice_mode",
        help=(
            "Turn this off for a realistic exam with feedback only at the end. "
            "When it is on, Victoria can correct spoken errors, suggest more precise "
            "expressions, and ask a slightly longer Part 3 for training."
        ),
    )

    st.toggle(
        "Personalized answer upgrade",
        key="answer_expansion_mode",
        disabled=not st.session_state.practice_mode,
        help=(
            "After your answer, Victoria preserves your idea and shows a natural "
            "two-to-three-sentence version at about IELTS Band 6.5-7 level."
        ),
    )

    st.toggle(
        "Read full feedback aloud",
        key="speak_full_reply",
        help=(
            "Off: Victoria only reads the next question or instruction aloud. "
            "On: Victoria reads corrections and upgraded answers as well."
        ),
    )

    current_part = {
        "identity": "Part 1",
        "part1": "Part 1",
        "part2_long": "Part 2",
        "part2_followup": "Part 2",
        "part3": "Part 3",
        "complete": "Complete",
    }.get(st.session_state.phase, "Part 1")
    st.info(f"Current stage: {current_part}")

    if st.session_state.phase == "part3":
        st.caption(
            f"Part 3 plan: {len(st.session_state.part3_questions)} main questions "
            "generated from the topic bank and your Part 2 answer."
        )
    else:
        planned_part3_count = get_part3_question_count()
        mode_label = "practice" if st.session_state.practice_mode else "mock-test"
        st.caption(
            f"Part 3 will use about {planned_part3_count} main questions in {mode_label} mode."
        )

    progress_value = {
        "identity": 0.05,
        "part1": 0.25,
        "part2_long": 0.5,
        "part2_followup": 0.65,
        "part3": 0.8,
        "complete": 1.0,
    }.get(st.session_state.phase, 0.05)
    st.progress(progress_value, text="Test progress")

    recorded_answers = [
        item
        for item in st.session_state.answer_stats
        if item["source"] == "audio" and item["duration"]
    ]
    if recorded_answers:
        total_audio_seconds = sum(item["duration"] for item in recorded_answers)
        st.caption(
            f"Recorded answers: {len(recorded_answers)} | "
            f"Speaking time: {total_audio_seconds:.1f}s"
        )

    timer_slot = st.empty()
    if "timer_end" in st.session_state and st.session_state.phase == "part2_long":
        with timer_slot.container():
            render_countdown(
                st.session_state.timer_end,
                st.session_state.get("timer_label", "Time remaining"),
            )

    if st.session_state.phase == "part2_long":
        if st.button("Start 2-minute speaking timer", use_container_width=True):
            st.session_state.timer_end = time.time() + 120
            st.session_state.timer_label = "Part 2 speaking time"
            st.rerun()

    st.divider()

    if st.button("Restart Test", use_container_width=True):
        reset_test()

    if st.button("End Test & Get Score", use_container_width=True):
        report_prompt = f"""
Create a clear IELTS Speaking practice report based ONLY on the raw candidate answers below.
Do not evaluate Victoria's feedback, corrections, upgraded answers, or prompts as if they were
the candidate's language.

Include:
1. An estimated overall band score, clearly labelled as an estimate.
2. Separate estimated bands for Fluency and Coherence, Lexical Resource, and
   Grammatical Range and Accuracy, each supported by evidence from the answers.
3. The candidate's three most important recurring spoken-language problems.
4. Three natural corrected examples based on the candidate's own meaning.
5. Two examples where a more precise or idiomatic expression would better match
   the candidate's intended meaning.
6. A focused seven-day improvement plan.

Audio timing information:
{audio_stats_summary()}

Raw answer log:
{export_candidate_answer_log()}

Use timing and speaking-rate data only when recorded audio was available.
Ignore spelling, capitalization, and punctuation because the answers are speech-to-text transcripts.
Focus on spoken grammar, word choice, semantic precision, fluency, coherence, and answer development.
State clearly that pronunciation cannot be assessed reliably without acoustic analysis.
"""
        with st.spinner("Victoria is preparing your report..."):
            try:
                report_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a strict but helpful IELTS Speaking examiner. "
                            "Score only the candidate's raw answers, not the coaching feedback."
                        ),
                    },
                    {"role": "user", "content": report_prompt},
                ]
                st.session_state.final_report = call_model(report_messages)
                st.session_state.test_active = False
            except Exception as error:
                st.error(f"The report could not be generated: {error}")

    st.download_button(
        "Download Transcript",
        data=export_transcript(),
        file_name="ielts_victoria_transcript.txt",
        mime="text/plain",
        use_container_width=True,
    )


# --- FINAL REPORT DISPLAY ---
if "final_report" in st.session_state:
    st.header("Final Exam Report")
    with st.container(border=True):
        st.markdown(st.session_state.final_report)
    if st.button("Start a New Test", use_container_width=True):
        reset_test()
    st.stop()


# --- DISPLAY CHAT ---
for message in st.session_state.messages:
    if message["role"] != "system":
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


# --- INPUT LOGIC ---
if st.session_state.test_active:
    user_input = None
    input_source = "text"
    answer_duration = None

    with st.expander("Record your answer", expanded=False):
        st.caption(
            "Your recording is sent to your configured GPTs API provider for English transcription."
        )
        recorder_key = st.session_state.audio_input_key
        recorded_audio = st.audio_input(
            "Speak in English",
            key=f"audio_answer_{recorder_key}",
        )

        if st.button(
            "Transcribe recording",
            disabled=recorded_audio is None,
            key=f"transcribe_audio_{recorder_key}",
            use_container_width=True,
        ):
            audio_bytes = recorded_audio.getvalue()
            with st.spinner("Transcribing your recording..."):
                try:
                    st.session_state.pending_transcript = transcribe_audio(audio_bytes)
                    st.session_state.pending_audio_duration = get_wav_duration(audio_bytes)
                except Exception as error:
                    st.error(
                        "Audio transcription is temporarily unavailable. "
                        f"You can still type your answer below. Details: {error}"
                    )

        if st.session_state.get("pending_transcript"):
            edited_transcript = st.text_area(
                "Review the transcript before submitting",
                value=st.session_state.pending_transcript,
                key=f"transcript_editor_{recorder_key}",
            )
            if st.button(
                "Submit recorded answer",
                key=f"submit_audio_{recorder_key}",
                type="primary",
                use_container_width=True,
            ):
                user_input = edited_transcript.strip()
                input_source = "audio"
                answer_duration = st.session_state.get("pending_audio_duration")
                st.session_state.audio_input_key += 1
                st.session_state.pop("pending_transcript", None)
                st.session_state.pop("pending_audio_duration", None)

    typed_input = st.chat_input("Type your answer, or use the recorder above...")
    if typed_input:
        user_input = typed_input
        input_source = "text"
        answer_duration = None

    if user_input:
        answer_phase = st.session_state.phase
        previous_question = st.session_state.current_question
        with st.chat_message("user"):
            st.markdown(user_input)
            if input_source == "audio" and answer_duration:
                st.caption(f"Recorded answer: {answer_duration:.1f} seconds")
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_answer_stats(user_input, input_source, answer_duration, answer_phase)
        record_candidate_answer(
            answer_phase,
            previous_question,
            user_input,
            input_source,
            answer_duration,
        )

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("*(Victoria is evaluating...)*")

            try:
                ai_reply, start_prep_timer, spoken_text = process_candidate_answer(
                    user_input,
                    previous_question,
                    answer_duration,
                )
                placeholder.markdown(ai_reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": ai_reply}
                )
            except Exception as error:
                placeholder.empty()
                st.error(f"Victoria could not respond: {error}")
            else:
                if start_prep_timer:
                    with timer_slot.container():
                        render_countdown(
                            st.session_state.timer_end,
                            st.session_state.timer_label,
                        )
                try:
                    speak_text(ai_reply if st.session_state.speak_full_reply else spoken_text)
                except Exception:
                    st.warning("The text reply worked, but audio could not be generated this time.")
