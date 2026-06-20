import io
import random
import re
import time

import streamlit as st
import streamlit.components.v1 as components
from gtts import gTTS
from openai import OpenAI


# --- CONFIGURATION ---
API_KEY = st.secrets["API_KEY"]
BASE_URL = "https://api.gptsapi.net/v1"
MODEL = "gpt-5.4-mini"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)


# --- TEST CONTENT ---
PART1_QUESTIONS = [
    "Do you work, or are you a student?",
    "What do you enjoy most about your work or studies?",
    "Is there anything you would like to change about your work or studies?",
    "Where is your hometown?",
    "What do you like most about your hometown?",
    "Has your hometown changed much in recent years?",
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

Return exactly one of these two formats:
NO_CORRECTION
CORRECTION: <one short, useful correction sentence>

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
- For a long answer with several errors, mention no more than three high-impact fixes
  in one concise sentence.

Examples:
- "you can call me water" -> NO_CORRECTION
- "architecture" -> NO_CORRECTION
- "achitecture" -> NO_CORRECTION
- "yes i do" -> NO_CORRECTION
- "maybe everyday" -> NO_CORRECTION
- "i am student" -> CORRECTION: Say "I am a student" because the spoken article "a" is missing.
- "it located in chengdu and it consist of four blocks" -> CORRECTION: Say "It is located in Chengdu and it consists of four blocks."
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


def evaluate_spoken_answer(answer):
    spoken_words = re.findall(r"[A-Za-z']+", answer)
    if len(spoken_words) <= 1:
        return None

    result = call_model(
        [
            {"role": "system", "content": CORRECTION_JUDGE_PROMPT},
            {"role": "user", "content": answer},
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


def build_reply(correction, next_content):
    if correction:
        return f"**Quick correction:** {correction}\n\n{next_content}"
    return next_content


# --- RELIABLE PROGRAM-CONTROLLED TEST FLOW ---
def process_candidate_answer(answer):
    correction = None
    if st.session_state.practice_mode:
        correction = evaluate_spoken_answer(answer)

    phase = st.session_state.phase
    start_prep_timer = False

    if phase == "identity":
        st.session_state.phase = "part1"
        st.session_state.part1_index = 1
        next_content = PART1_QUESTIONS[0]

    elif phase == "part1":
        index = st.session_state.part1_index
        if index < len(PART1_QUESTIONS):
            next_content = PART1_QUESTIONS[index]
            st.session_state.part1_index += 1
        else:
            st.session_state.phase = "part2_long"
            st.session_state.part2_words = 0
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
        if (
            st.session_state.part2_words < 80
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

    return build_reply(correction, next_content), start_prep_timer


# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": EXAM_CONTEXT},
        {"role": "assistant", "content": FIRST_MESSAGE},
    ]
    st.session_state.phase = "identity"
    st.session_state.part1_index = 0
    st.session_state.part3_index = 0
    st.session_state.part2_words = 0
    st.session_state.part2_extension_used = False
    st.session_state.cue_card = random.choice(CUE_CARDS)
    st.session_state.test_active = True
    st.session_state.practice_mode = True


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
        report_prompt = """
Create a concise IELTS Speaking practice report from this conversation.
Include:
1. An estimated overall band score, clearly labelled as an estimate.
2. Feedback on Fluency and Coherence, Lexical Resource, and Grammatical Range and Accuracy.
3. Three practical improvement priorities with corrected examples from the candidate's answers.
Ignore spelling, capitalization, and punctuation because the answers are speech-to-text transcripts.
State clearly that pronunciation cannot be assessed reliably from text alone.
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
    if user_input := st.chat_input("Speak to Victoria..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("*(Victoria is evaluating...)*")

            try:
                ai_reply, start_prep_timer = process_candidate_answer(user_input)
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
