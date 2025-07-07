import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import av
import queue
import numpy as np
import tempfile
import os

# Configuration
st.set_page_config(page_title="FANG Mock Interview (Voice)", layout="centered")
st.title("🎤 FANG Mock Interview")

# Input fields
role = st.text_input("Role (e.g., Software Engineer)")
company = st.text_input("Company (e.g., Google)")

# OpenAI Client
if "openai_api_key" not in st.secrets:
    st.error("OpenAI API key missing in `.streamlit/secrets.toml`")
    st.stop()
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Constants
MAX_QUESTIONS = 5
MIN_DURATION_SECONDS = 30
audio_q = queue.Queue()

# System prompt generator
def get_company_values(name):
    name = name.lower()
    if "amazon" in name: return "Amazon’s Leadership Principles"
    if "google" in name: return "Google’s innovation culture"
    if "meta" in name: return "Meta’s boldness and impact focus"
    if "netflix" in name: return "Netflix’s freedom & responsibility culture"
    if "apple" in name: return "Apple’s quality and design-first approach"
    return "top-tier engineering principles"

def system_prompt(role, company):
    values = get_company_values(company)
    return (
        f"You are a senior engineer at {company.title()} conducting a mock interview for a {role} position. "
        f"Ask {MAX_QUESTIONS} structured questions, one at a time. Wait for the candidate's answer after each. "
        f"After all answers, provide detailed feedback and a score out of 25."
    )

# Audio Processor
class AudioProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.recording = b""
    
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        audio = frame.to_ndarray().flatten().astype(np.int16).tobytes()
        audio_q.put(audio)
        return frame

# Initialize state
if role and company:
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
        st.session_state.answers = []
        st.session_state.question_index = 0
        st.session_state.awaiting_question = True
        st.session_state.final_feedback = None
        st.session_state.recorded_audio = b""
        st.success("Welcome! Your mock interview is starting.")

    # Ask question
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

    # WebRTC Setup
    webrtc_ctx = webrtc_streamer(
        key="speech",
        mode=WebRtcMode.SENDONLY,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
    )

    # Recording logic
    if webrtc_ctx.state.playing:
        st.info("🎙️ Recording... Click 'Done' when you're finished answering (30+ seconds).")

    if st.button("✅ Done"):
        st.info("Processing your answer...")
        # Collect all audio
        audio = b""
        while not audio_q.empty():
            audio += audio_q.get()

        duration_seconds = len(audio) / (16000 * 2)  # 16kHz, 16-bit PCM
        if duration_seconds < MIN_DURATION_SECONDS:
            st.warning(f"Your answer was only {int(duration_seconds)} seconds. Please speak for at least {MIN_DURATION_SECONDS} seconds.")
        else:
            # Save to file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio)
                tmp_path = tmp.name

            with open(tmp_path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            os.remove(tmp_path)

            answer = transcription.text
            st.chat_message("user").markdown(answer)
            st.session_state.messages.append({"role": "user", "content": answer})
            st.session_state.answers.append(answer)

            # Next question
            st.session_state.question_index += 1
            st.session_state.awaiting_question = True

    # Final feedback
    if st.session_state.question_index == MAX_QUESTIONS and st.session_state.final_feedback is None:
        st.session_state.messages.append({
            "role": "user",
            "content": "The candidate has answered all questions. Provide full feedback and score (out of 25)."
        })
        stream = client.chat.completions.create(
            model="gpt-4",
            messages=st.session_state.messages,
            stream=True,
        )
        with st.chat_message("assistant"):
            feedback = st.write_stream(stream)
        st.session_state.final_feedback = feedback
        st.session_state.messages.append({"role": "assistant", "content": feedback})
