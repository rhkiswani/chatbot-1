import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
import av
import numpy as np
import tempfile
import os
import queue
import wave
import contextlib
import time

# Constants
MAX_QUESTIONS = 5
MIN_DURATION_SECONDS = 30
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # 2 bytes for int16
audio_q = queue.Queue()

# Title
st.title("🎤 FANG Mock Interview (Live Voice)")
st.write("Answer questions with your voice. The app will transcribe your responses using OpenAI Whisper.")

# Role and company input
role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

# OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Please add your OpenAI key to `.streamlit/secrets.toml`")
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

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
            f"Ask {MAX_QUESTIONS} structured questions, one at a time. Wait for the candidate's answer after each. "
            f"After all answers, provide detailed feedback and a score out of 25."
        )

    if role and company:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
            st.session_state.question_index = 0
            st.session_state.answers = []
            st.session_state.awaiting_question = True
            st.session_state.final_feedback = None
            st.session_state.audio_recording = bytearray()
            st.session_state.recording_start = None

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

        current_question = st.session_state.messages[-1]["content"]
        st.markdown(f"**🧠 Question {st.session_state.question_index + 1}:** {current_question}")
        st.markdown("🎙️ Please speak for at least 30 seconds. Click below when you're done.")

        # Audio processor
        class AudioProcessor(AudioProcessorBase):
            def __init__(self) -> None:
                self.start_time = None

            def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
                audio = frame.to_ndarray().flatten().astype(np.int16).tobytes()
                audio_q.put(audio)
                return frame

        # Start mic
        webrtc_ctx = webrtc_streamer(
            key="live-audio",
            mode="sendonly",
            audio_receiver_size=1024,
            audio_processor_factory=AudioProcessor,
            media_stream_constraints={"audio": True, "video": False},
            async_processing=True
        )

        def record_and_transcribe():
            st.session_state.audio_recording = bytearr
