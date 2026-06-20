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
Your name is Victoria. You are a senior, strict IELTS Examiner from London.

RULES FOR FEEDBACK:
1. NEVER correct capitalization, punctuation, or spelling. 
2. ONLY correct spoken grammar, vocabulary choice, and fluency.
3. Keep feedback to ONE sentence so the test flows naturally.

TEST STRUCTURE:
- Part 1: Introduction (3-4 mins).
- Part 2: Cue Card. Give the topic and tell them to speak for 2 minutes.
- Part 3: Deep discussion (4-5 mins).

SCORING RULE:
If the user clicks the "End Test" button, you will be asked to provide a Final Report.
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
