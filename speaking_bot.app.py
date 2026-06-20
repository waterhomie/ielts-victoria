import streamlit as st
from openai import OpenAI
from gtts import gTTS
import io
import base64
import time

# --- CONFIGURATION ---
API_KEY = st.secrets["API_KEY"]
BASE_URL = "https://api.gptsapi.net/v1" 

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- WEB APP SETUP ---
st.set_page_config(page_title="IELTS Victoria Pro", page_icon="🎓", layout="centered")

# Custom CSS for a cleaner look
st.markdown("""
    <style>
    .stChatFloatingInputContainer {padding-bottom: 20px;}
    .report-box {background-color: #f0f2f6; padding: 20px; border-radius: 10px; border: 1px solid #d1d5db;}
    </style>
    """, unsafe_allow_html=True)

st.title("🎓 Examiner Victoria (Pro)")
st.caption("Professional IELTS Speaking Simulator with Band Scoring")

# --- THE UPGRADED PERSONA ---
system_prompt = """
Your name is Victoria. You are a professional IELTS Speaking Examiner and speaking coach from London.

GENERAL RULES:
- The test begins immediately with Part 1.
- The full-name question is the beginning of Part 1, not pre-test conversation.
- NEVER ask the candidate which part they want to start with.
- NEVER ask whether they are ready to continue.
- Follow the order Part 1, then Part 2, then Part 3 automatically.
- Ask exactly ONE question at a time.

PART 1:
- After asking the candidate's full name, ask exactly SIX Part 1 questions.
- Use two familiar IELTS topics such as work, studies, hometown, home, hobbies, food, transport, or daily life.
- After the sixth Part 1 question, move directly to Part 2 without asking permission.

PART 2:
- Give one IELTS cue card.
- Tell the candidate they have one minute to prepare and should speak for one to two minutes.
- After their answer, ask one short follow-up question.
- Then move directly to Part 3 without asking permission.

PART 3:
- Ask FOUR deeper discussion questions related to the Part 2 topic.
- Ask them one at a time.

FEEDBACK RULES:
- NEVER correct capitalization, punctuation, spelling, or obvious speech-to-text errors.
- Capitalization and punctuation cannot be heard in spoken English.
- Do not correct a word merely because the transcription is misspelled.
- ONLY correct genuine spoken grammar, vocabulary choice, sentence structure, or fluency problems.
- Give no correction when the spoken answer is already natural and correct.
- Keep feedback to one short sentence.

MANDATORY TURN FLOW:
For every candidate answer:
1. Give one brief correction only when there is a genuine spoken-language error.
2. Immediately ask the next IELTS question in the SAME message.

NEVER stop after correcting.
NEVER wait for the candidate to say "OK" or "continue".
NEVER ask the candidate to choose Part 1, Part 2, or Part 3.

If the user clicks the "End Test" button, provide a formal IELTS report with an estimated band score and practical improvement advice.
"""

# --- AUDIO FUNCTION ---
def speak_text(text):
    clean_text = text.replace("*", "").replace("#", "").replace("- ", "")
    tts = gTTS(text=clean_text, lang='en', tld='co.uk')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    b64 = base64.b64encode(fp.read()).decode()
    audio_html = f'<audio src="data:audio/mp3;base64,{b64}" controls autoplay style="width:100%;"></audio>'
    st.markdown(audio_html, unsafe_allow_html=True)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_prompt}]
    first_msg = "Good afternoon. My name is Victoria. I will be your examiner today. Can you tell me your full name, please?"
    st.session_state.messages.append({"role": "assistant", "content": first_msg})
    st.session_state.test_active = True

# --- SIDEBAR TOOLS ---
with st.sidebar:
    st.header("Exam Tools")
    if st.button("⏱️ Start Part 2 Timer (120s)"):
        timer_placeholder = st.empty()
        for i in range(120, 0, -1):
            timer_placeholder.metric("Time Remaining", f"{i}s")
            time.sleep(1)
        timer_placeholder.error("Time is up! Wrap up your sentence.")
        
    st.divider()
    if st.button("📊 End Test & Get Score"):
        st.session_state.test_active = False
        with st.spinner("Victoria is calculating your Band Score..."):
            report_prompt = "Based on our conversation above, provide a formal IELTS Report. Include: 1. Estimated Band Score (0-9). 2. Feedback on Fluency, Lexical Resource, and Grammar. 3. Top 3 tips to improve."
            st.session_state.messages.append({"role": "user", "content": report_prompt})
            response = client.chat.completions.create(model="gpt-5.4-mini", messages=st.session_state.messages)
            st.session_state.final_report = response.choices[0].message.content

# --- FINAL REPORT DISPLAY ---
if not st.session_state.test_active and "final_report" in st.session_state:
    st.header("📋 Final Exam Report")
    st.markdown(f'<div class="report-box">{st.session_state.final_report}</div>', unsafe_allow_html=True)
    if st.button("Restart New Test"):
        for key in st.session_state.keys(): del st.session_state[key]
        st.rerun()
    st.stop()

# --- DISPLAY CHAT ---
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# --- INPUT LOGIC ---
if st.session_state.test_active:
    if user_input := st.chat_input("Speak to Victoria..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("*(Victoria is evaluating...)*")
            
            response = client.chat.completions.create(
                model="gpt-5.4-mini",
                messages=st.session_state.messages
            )
            ai_reply = response.choices[0].message.content
            placeholder.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            speak_text(ai_reply)
