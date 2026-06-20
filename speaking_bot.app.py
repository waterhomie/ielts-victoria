import io
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
st.caption("Professional IELTS Speaking Practice with Band Scoring")


# --- EXAMINER INSTRUCTIONS ---
system_prompt = """
Your name is Victoria. You are a professional IELTS Speaking Examiner from London.
You are not a writing teacher and must never edit the candidate's transcript.

GENERAL RULES:
- Treat every user message as a speech-to-text transcript, never as written English.
- The test starts immediately with Part 1.
- The full-name question is the beginning of Part 1, not pre-test conversation.
- Follow Part 1, Part 2, and Part 3 in order.
- Never ask which part the candidate wants to start with.
- Never ask whether the candidate is ready or wants to continue.
- Ask exactly one question at a time.
- Obey the STAGE CONTROL instruction supplied for each turn.

FEEDBACK RULES — HIGHEST PRIORITY:
- Before correcting, silently ask: "Can this error actually be heard?"
- If the error cannot be heard, correction is forbidden.
- Never correct capitalization, punctuation, spelling, formatting, or obvious transcription errors.
- Never rewrite an answer that is already correct when spoken aloud.
- A misspelled single-word answer is not a spoken error.
- If a misspelled word answers the question, accept it and continue.
- Only correct genuine spoken grammar, vocabulary choice, sentence structure, or fluency problems.
- Keep any correction to one short sentence.

MANDATORY RESPONSE FLOW:
- If there is no audible spoken-language error, do not say "You can say", "You could say", or "You should say". Briefly acknowledge the answer and ask the next question.
- If there is a genuine audible error, begin with "Better:" and give one short correction. Then ask the next question in the same message.
- Never stop after feedback and never wait for "OK" or "continue".

EXAMPLES:
- Candidate: "you can call me water"
  Correct response: "Thank you, Water. Do you work, or are you a student?"
- Candidate: "achitecture"
  Correct response: "I see. Why did you choose architecture?"
- Candidate: "yes i do"
  Give no correction because capitalization cannot be heard.
- Candidate: "i am student"
  Correct the missing spoken article: "Better: I am a student. What subject do you study?"

PART 1:
- Ask six questions across two familiar topics after the candidate gives their name.

PART 2:
- Give one IELTS cue card.
- Allow one minute to prepare and ask the candidate to speak for one to two minutes.
- Ask one brief follow-up question after the long answer.

PART 3:
- Ask four deeper questions related to the Part 2 topic, one at a time.

When the test is complete, thank the candidate and tell them to click "End Test & Get Score".
"""

FIRST_MESSAGE = (
    "Good afternoon. My name is Victoria, and I will be your examiner today. "
    "Could you tell me your full name, please?"
)


# --- HELPERS ---
def call_model(messages, turn_instruction=None):
    request_messages = list(messages)
    if turn_instruction:
        request_messages.insert(
            1,
            {"role": "system", "content": turn_instruction},
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=request_messages,
    )
    return response.choices[0].message.content


def speak_text(text):
    clean_text = text.replace("*", "").replace("#", "").replace("- ", "")
    audio_buffer = io.BytesIO()
    gTTS(text=clean_text, lang="en", tld="co.uk").write_to_fp(audio_buffer)
    st.audio(audio_buffer.getvalue(), format="audio/mp3", autoplay=True)


def candidate_turn_count():
    return sum(message["role"] == "user" for message in st.session_state.messages)


def stage_instruction(turn_number):
    if turn_number == 1:
        return "STAGE CONTROL: The candidate has given their name. Ask Part 1 question 1 of 6."
    if 2 <= turn_number <= 6:
        return f"STAGE CONTROL: Stay in Part 1. Ask question {turn_number} of 6."
    if turn_number == 7:
        return "STAGE CONTROL: Part 1 is complete. Move directly to Part 2 and give a cue card now."
    if turn_number == 8:
        return "STAGE CONTROL: The Part 2 long answer is complete. Ask one brief Part 2 follow-up question."
    if turn_number == 9:
        return "STAGE CONTROL: Move directly to Part 3 and ask question 1 of 4."
    if 10 <= turn_number <= 12:
        question_number = turn_number - 8
        return f"STAGE CONTROL: Stay in Part 3. Ask question {question_number} of 4."
    return (
        "STAGE CONTROL: The speaking test is complete. Thank the candidate and tell them "
        "to click 'End Test & Get Score'. Do not ask another question."
    )


def reset_test():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


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


# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": system_prompt},
        {"role": "assistant", "content": FIRST_MESSAGE},
    ]

if "test_active" not in st.session_state:
    st.session_state.test_active = True


# --- SIDEBAR TOOLS ---
with st.sidebar:
    st.header("Exam Tools")

    timer_col_1, timer_col_2 = st.columns(2)
    if timer_col_1.button("Start 1-min prep", use_container_width=True):
        st.session_state.timer_end = time.time() + 60
        st.session_state.timer_label = "Preparation time"
    if timer_col_2.button("Start 2-min talk", use_container_width=True):
        st.session_state.timer_end = time.time() + 120
        st.session_state.timer_label = "Speaking time"

    if "timer_end" in st.session_state:
        render_countdown(
            st.session_state.timer_end,
            st.session_state.get("timer_label", "Time remaining"),
        )

    st.divider()

    if st.button("Restart Test", use_container_width=True):
        reset_test()

    if st.button("End Test & Get Score", use_container_width=True):
        report_prompt = """
Create a concise IELTS Speaking practice report from the conversation.
Include:
1. An estimated overall band score, clearly labelled as an estimate.
2. Feedback on Fluency and Coherence, Lexical Resource, and Grammatical Range and Accuracy.
3. Three practical improvement priorities.
Do not assess spelling, capitalization, or punctuation because the answers are speech-to-text transcripts.
State that pronunciation cannot be reliably assessed from text alone.
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
if not st.session_state.test_active and "final_report" in st.session_state:
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
                instruction = stage_instruction(candidate_turn_count())
                ai_reply = call_model(st.session_state.messages, instruction)
                placeholder.markdown(ai_reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": ai_reply}
                )
            except Exception as error:
                placeholder.empty()
                st.error(f"Victoria could not respond: {error}")
            else:
                try:
                    speak_text(ai_reply)
                except Exception:
                    st.warning("The text reply worked, but audio could not be generated this time.")
