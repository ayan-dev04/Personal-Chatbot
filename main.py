import os
import sqlite3
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Nexus AI", page_icon="🤖", layout="wide")
load_dotenv()

# 2. Modern Client Initialization
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# STEP 1: FIND A WORKING MODEL AUTOMATICALLY
def get_working_model():
    """Finds the best available model for your specific API key."""
    try:
        # We try 2.5 first as it's the current standard
        available_models = [m.name for m in client.models.list() if 'generateContent' in m.supported_generation_methods]
        preferred = ["models/gemini-2.5-flash", "models/gemini-flash-latest", "models/gemini-2.0-flash"]

        for p in preferred:
            if p in available_models:
                return p.replace("models/", "")  # SDK expects name without 'models/' prefix

        # Fallback to the first available if preferred ones aren't found
        return available_models[0].replace("models/", "") if available_models else "gemini-2.5-flash"
    except:
        return "gemini-2.5-flash"  # Hard fallback


MODEL_ID = get_working_model()
SYSTEM_INSTRUCTION = "You are Nexus AI. Provide clear, technical, and formatted responses."


# 3. Database & UI Logic (Keeping your existing history logic)
def init_db():
    conn = sqlite3.connect('chat_history.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS logs (role TEXT, content TEXT, timestamp DATETIME)''')
    conn.commit()
    return conn


def save_to_db(role, content):
    conn = init_db()
    c = conn.cursor();
    c.execute("INSERT INTO logs (role, content, timestamp) VALUES (?, ?, ?)", (role, content, datetime.now()))
    conn.commit();
    conn.close()


# 4. Sidebar & History
with st.sidebar:
    st.title("🤖 Nexus AI Settings")
    st.info(f"Active Model: {MODEL_ID}")  # Shows you which model it found
    if st.button("🗑️ Reset Conversations"):
        conn = init_db();
        conn.cursor().execute("DELETE FROM logs");
        conn.commit()
        st.session_state.messages = [];
        st.rerun()

# 5. Main Chat Logic
st.title("Nexus AI")
if "messages" not in st.session_state:
    conn = init_db();
    df = pd.read_sql_query("SELECT * FROM logs ORDER BY timestamp ASC", conn)
    st.session_state.messages = df.to_dict('records')

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Ask a question..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_to_db("user", prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION)
            )
            ai_text = response.text
            message_placeholder.markdown(ai_text)
            st.session_state.messages.append({"role": "assistant", "content": ai_text})
            save_to_db("assistant", ai_text)
        except Exception as e:
            st.error(f"Technical Error: {e}")