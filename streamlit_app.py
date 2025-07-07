import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import numpy as np
import tempfile
import os
import queue

# Page setup
st.set_page_config(page_title="FANG Mock Interview (Voice)", page_icon="🎤")
st.title("🎤 FANG Mock Interview")
st.write("Answer questions with your voice. Your responses will be transcribed and evaluated.")

# Inputs
role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

MAX_QUESTIONS = 5
audio_q = queue.Queue()

# Validate API key
if "openai_api_key" not in st.secrets:
    st.error("❌ Please add your OpenAI key to `.streamlit/secrets.toml`")
    st.stop()

# Setup OpenAI client
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Helpers
def get_company_values(name):
    name = name.lower()
    if "amazon" in name:
        return "Amazon’s Leadership Principles"
    elif "google" in name:
        return "Google’s innovation culture"
    elif "meta" in name:
        return "Meta’s boldness and impact focus"
    elif "netflix" in name:
        return "Netflix’s freedom & responsibility culture"
    elif "apple" in name:
        return "Apple’s quality and design-first approach"
    else:
        return "top-tier engineering principles"

def system_prompt(role, company):
    values = get_company_values(company)
    return (
        f"You are a senior engineer at {company.title()} conducting a mock interview for a {role} position. "
        f"Ask {MAX_QUESTIONS} structured, realistic questions — one at a time. "
        f"Wait for each answer before asking the next. "
        f"At the end, provide detailed feedback and a score out of 25."
    )

# Initialize session state
if role and company:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
        st.session_state.question_index = 0
        st.session_state.answers = []
        st.session_state.awaiting_question = True
        st.session_state.final_feedback = None
        st.session_state.audio_recording = b""
        st.session_state.welcomed = False

    # Welcome message
    if not st.session_state.welcomed:
        st.success(f"🎉 Welcome to your mock interview for the {role} role at {company}!")
        st.session_state.welcomed = True

    # Ask next question
    if st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
        st.session_state.messages.append({
            "role": "user",
            "content": f"Ask question #{st.session_state.question_index + 1}"
        })
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state.messages,
            stream=True,
        )
        with st.chat_message("assistant"):
            question = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": question})
        st.session_state.awaiting_question = False

    # Define audio processor
    class AudioProcessor(AudioProcessorBase):
        def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
            audio = frame.to_ndarray().flatten().astype(np.int16).tobytes()
            audio_q.put(audio)
            return frame

    # Start audio stream
    webrtc_ctx = webrtc_streamer(
        key="voice-interview",
        mode="sendonly",
        audio_receiver_size=1024,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
    )

    # Record and transcribe
    def record_and_transcribe():
        audio_data = b""
        while webrtc_ctx.state.playing:
            try:
                chunk = audio_q.get(timeout=5)
                audio_data += chunk
            except queue.Empty:
                break

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        os.remove(tmp_path)
        return transcript.text

    # Record button
    if st.button("🎙️ Submit Voice Answer"):
        with st.spinner("Transcribing..."):
            result = record_and_transcribe()
            st.session_state.answers.append(result)
            st.session_state.messages.append({"role": "user", "content": result})
            with st.chat_message("user"):
                st.markdown(result)
            st.session_state.question_index += 1
            st.session_state.awaiting_question = True

    # Final feedback
    if st.session_state.question_index == MAX_QUESTIONS and not st.session_state.final_feedback:
        st.session_state.messages.append({
            "role": "user",
            "content": "The candidate has answered all questions. Please give feedback and a score out of 25."
        })
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state.messages,
            stream=True,
        )
        with st.chat_message("assistant"):
            final = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": final})
        st.session_state.final_feedback = final

    # Restart interview
    if st.session_state.question_index == MAX_QUESTIONS:
        if st.button("🔁 Start New Interview"):
            for key in [
                "messages", "question_index", "answers", "awaiting_question",
                "final_feedback", "audio_recording", "welcomed"
            ]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
