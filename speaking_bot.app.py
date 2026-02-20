import streamlit as st
from openai import OpenAI
from gtts import gTTS
import io
import base64

# --- CONFIGURATION ---
API_KEY = "sk-G8Q0c6064d94bb663ba726b7d6564ea3807451c218atKtqS"
BASE_URL = "https://api.gptsapi.net/v1" 

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- WEB APP SETUP ---
st.set_page_config(page_title="IELTS Victoria", page_icon="🎓", layout="centered")
st.title("🎓 Examiner Victoria")
st.caption("Tip: Keep your answers under 1 minute for the fastest performance.")

# --- THE FIXED PERSONA ---
# I have hardcoded her name here so she doesn't use placeholders.
# --- THE UPDATED SYSTEM PROMPT ---
system_prompt = """
Your name is Victoria. You are a professional, senior IELTS Speaking Examiner from London.
You are strict but fair.

CRITICAL INSTRUCTIONS FOR FEEDBACK:
1. IGNORE all capitalization, punctuation, and spelling errors. (The user is using Speech-to-Text; these are not their mistakes).
2. ONLY provide feedback on spoken performance:
   - Grammar (e.g., Verb tenses, word order).
   - Vocabulary (e.g., Suggesting more advanced/precise synonyms).
   - Sentence structure and Fluency.
3. Keep corrections very brief (1 sentence) before asking the next question.

CONDUCT THE TEST IN 3 PARTS:
1. Part 1: Small talk questions.
2. Part 2: Give the user a Topic Card (cue card) and ask them to speak for 1-2 minutes.
3. Part 3: Deep discussion related to the Part 2 topic.

Start now by saying: "Good afternoon. My name is Victoria, and I will be your examiner today. To begin, could you tell me your full name, please?"
"""
# --- MEMORY (SESSION STATE) ---
if "messages" not in st.session_state:
    st.session_state.messages = list()
    st.session_state.messages.append({"role": "system", "content": system_prompt})
    
    # First message is now pre-set to speed up the very first load
    first_msg = "Good afternoon. My name is Victoria, and I will be your examiner today. To begin, could you tell me your full name, please?"
    st.session_state.messages.append({"role": "assistant", "content": first_msg})

# --- DISPLAY CHAT ---
for msg in st.session_state.messages:
    if msg.get("role") != "system":
        with st.chat_message(msg.get("role")):
            st.markdown(msg.get("content"))

# --- CHAT INPUT ---
user_input = st.chat_input("Dictate your answer to Victoria...")

if user_input:
    with st.chat_message("user"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("*(Victoria is listening...)*")
        
        try:
            # Using GPT-3.5-Turbo for maximum speed
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=st.session_state.messages,
                temperature=0.7 # Makes her sound more natural
            )
            ai_reply = response.choices[0].message.content
            placeholder.markdown(ai_reply)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            
            # --- FASTER AUDIO GENERATION ---
            clean_text = ai_reply.replace("*", "").replace("#", "").replace("- ", "")
            tts = gTTS(text=clean_text, lang='en', tld='co.uk')
            
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            b64 = base64.b64encode(fp.read()).decode()
            audio_html = f'<audio src="data:audio/mp3;base64,{b64}" controls autoplay style="width:100%; margin-top:10px;"></audio>'
            st.markdown(audio_html, unsafe_allow_html=True)
            
        except Exception as e:
            st.error(f"Victoria encountered an error: {e}")