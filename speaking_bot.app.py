import io
import random
import re
import time
import wave

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from openai import OpenAI

from question_bank import EXTRA_CUE_CARDS, PART1_SECONDARY_TOPICS


# --- CONFIGURATION ---
API_KEY = st.secrets["API_KEY"]
BASE_URL = "https://api.gptsapi.net/v1"
MODEL = "gpt-5.4-mini"
TRANSCRIPTION_MODEL = "whisper-1"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# --- TEST CONTENT ---
PART1_FIRST_QUESTION = "Do you work, or are you a student?"

PART1_STUDENT_FOLLOWUPS = [
    "What subject are you studying?",
    "What do you enjoy most about your studies?",
]

PART1_WORK_FOLLOWUPS = [
    "What kind of work do you do?",
    "What do you enjoy most about your job?",
]

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

CORRECTION_JUDGE_PROMPT = """
You are a strict spoken-English error judge for an IELTS practice app.
The candidate's answer is a speech-to-text transcript, not written English.
Use the examiner's question to understand the intended meaning, tense, and context.

Return exactly one of these two formats:
NO_CORRECTION
CORRECTION: <one natural corrected version, no more than 30 words>

Rules:
- Silently ask: "Could this error actually be heard?"
- If it could not be heard, return NO_CORRECTION.
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

Examples:
- Question: "Could you tell me your name?" Answer: "you can call me water"
  -> NO_CORRECTION
- Question: "What subject do you study?" Answer: "achitecture"
  -> NO_CORRECTION
- Question: "Do you enjoy your studies?" Answer: "yes i do"
  -> NO_CORRECTION
- Question: "What do you enjoy most about your studies?" Answer: "i prefer study"
  -> CORRECTION: I prefer studying.
- Question: "Has your hometown changed much?"
  Answer: "yes it become more quiet because of the youth loss"
  -> CORRECTION: Yes, it has become quieter because many young people have moved away.
- Question: "Would you visit the building again?"
  Answer: "yes because you feel ease and relaxation when you in the space"
  -> CORRECTION: Yes, because I feel relaxed and at ease when I am inside.
"""


# --- WEB APP SETUP ---
st.set_page_config(
    page_title="IELTS Victoria Pro",
    page_icon="🎓",
    layout="centered",
)

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


def evaluate_spoken_answer(question, answer):
    spoken_words = re.findall(r"[A-Za-z']+", answer)
    if len(spoken_words) <= 1:
        return None

    result = call_model(
        [
            {"role": "system", "content": CORRECTION_JUDGE_PROMPT},
            {
                "role": "user",
                "content": (
                    f"EXAMINER QUESTION:\n{question}\n\n"
                    f"CANDIDATE ANSWER:\n{answer}"
                ),
            },
        ]
    )

    if result.upper().startswith("NO_CORRECTION"):
        return None
    if result.upper().startswith("CORRECTION:"):
        correction = result.split(":", 1)[1].strip()
        return correction or None

    # Safe default: never display an unstructured or uncertain correction.
    return None


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
        personal_questions = PART1_STUDENT_FOLLOWUPS
    elif re.search(r"\b(work|working|job|employed|employee)\b", normalized):
        personal_questions = PART1_WORK_FOLLOWUPS
    else:
        personal_questions = PART1_GENERAL_FOLLOWUPS

    return personal_questions + st.session_state.part1_secondary_questions


def build_reply(correction, expansion_tip, next_content):
    sections = []
    if correction:
        sections.append(f"**Quick correction:** {correction}")
    if expansion_tip:
        sections.append(f"**Expansion tip:** {expansion_tip}")
    sections.append(next_content)
    return "\n\n".join(sections)


# --- RELIABLE PROGRAM-CONTROLLED TEST FLOW ---
def process_candidate_answer(answer, previous_question, answer_duration=None):
    phase = st.session_state.phase
    correction = None
    if st.session_state.practice_mode:
        correction = evaluate_spoken_answer(previous_question, answer)

    expansion_tip = None
    answer_word_count = len(re.findall(r"[A-Za-z']+", answer))
    if (
        st.session_state.practice_mode
        and phase in {"part1", "part3"}
        and not (phase == "part1" and not st.session_state.part1_queue)
        and correction is None
        and answer_word_count <= 3
        and st.session_state.expansion_tips_used < 2
    ):
        expansion_tip = "Add one reason or example so you can demonstrate more fluency."
        st.session_state.expansion_tips_used += 1

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
        st.session_state.phase = "part3"
        st.session_state.part3_index = 1
        next_content = (
            "**Part 3 - Discussion**\n\n"
            + st.session_state.cue_card["part3"][0]
        )

    elif phase == "part3":
        index = st.session_state.part3_index
        questions = st.session_state.cue_card["part3"]
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

    return build_reply(correction, expansion_tip, next_content), start_prep_timer


# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": EXAM_CONTEXT},
        {"role": "assistant", "content": FIRST_MESSAGE},
    ]
    st.session_state.phase = "identity"
    st.session_state.part1_index = 0
    st.session_state.part1_queue = []
    st.session_state.part1_secondary_questions = list(
        random.choice(PART1_SECONDARY_TOPICS)["questions"]
    )
    st.session_state.part3_index = 0
    st.session_state.part2_words = 0
    st.session_state.part2_duration = 0.0
    st.session_state.part2_audio_used = False
    st.session_state.part2_extension_used = False
    st.session_state.expansion_tips_used = 0
    st.session_state.cue_card = random.choice(CUE_CARDS)
    st.session_state.current_question = FIRST_MESSAGE
    st.session_state.test_active = True
    st.session_state.practice_mode = True
    st.session_state.answer_stats = []
    st.session_state.audio_input_key = 0


# --- SIDEBAR TOOLS ---
with st.sidebar:
    st.header("Exam Tools")

    st.toggle(
        "Practice mode - instant spoken corrections",
        key="practice_mode",
        help="Turn this off for a realistic exam with feedback only at the end.",
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
Create a clear IELTS Speaking practice report from this conversation.

Include:
1. An estimated overall band score, clearly labelled as an estimate.
2. Separate estimated bands for Fluency and Coherence, Lexical Resource, and
   Grammatical Range and Accuracy, each supported by evidence from the answers.
3. The candidate's three most important recurring spoken-language problems.
4. Three natural corrected examples based on the candidate's own meaning.
5. A focused seven-day improvement plan.

Audio timing information:
{audio_stats_summary()}

Use timing and speaking-rate data only when recorded audio was available.
Ignore spelling, capitalization, and punctuation because the answers are speech-to-text transcripts.
State clearly that pronunciation cannot be assessed reliably without acoustic analysis.
"""
        with st.spinner("Victoria is preparing your report..."):
            try:
                report_messages = st.session_state.messages + [
                    {"role": "user", "content": report_prompt}
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
        with st.chat_message("user"):
            st.markdown(user_input)
            if input_source == "audio" and answer_duration:
                st.caption(f"Recorded answer: {answer_duration:.1f} seconds")
        st.session_state.messages.append({"role": "user", "content": user_input})
        save_answer_stats(user_input, input_source, answer_duration, answer_phase)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("*(Victoria is evaluating...)*")

            try:
                ai_reply, start_prep_timer = process_candidate_answer(
                    user_input,
                    st.session_state.current_question,
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
                    speak_text(ai_reply)
                except Exception:
                    st.warning("The text reply worked, but audio could not be generated this time.")
