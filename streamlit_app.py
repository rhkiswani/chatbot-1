import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av
import numpy as np
import tempfile
import os
import wave

# Setup
st.title("🎤 FANG Mock Interview (Live Voice)")
st.write("Answer questions with your voice. The app will transcribe your responses using OpenAI Whisper.")

role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

MAX_QUESTIONS = 5
MIN_DURATION_SECONDS = 30

# OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Add your OpenAI key to `.streamlit/secrets.toml`")
    st.stop()

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

# Audio Processor
class AudioProcessor(AudioProcessorBase):
    def __init__(self) -> None:
        self.frames = []

    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        pcm = frame.to_ndarray().flatten().astype(np.int16).tobytes()
        self.frames.append(pcm)
        return frame

    def get_wav(self):
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        with wave.open(temp_file, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)
            wf.writeframes(b''.join(self.frames))
        return temp_file.name

if role and company:
    st.markdown(f"### Welcome to your {role} mock interview at {company}! 🎉")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
        st.session_state.question_index = 0
        st.session_state.answers = []
        st.session_state.awaiting_question = True
        st.session_state.final_feedback = None

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

    # Mic recording section
    st.markdown("#### 🎙️ Please speak your answer below (min 30 seconds)")

    webrtc_ctx = webrtc_streamer(
        key="speech",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        audio_processor_factory=AudioProcessor,
        media_stream_constraints={"audio": True, "video": False},
        async_processing=True,
    )

    # Submit
    if st.button("✅ Done"):
        if webrtc_ctx.audio_processor:
            st.info("Processing your answer...")
            wav_path = webrtc_ctx.audio_processor.get_wav()
            duration = os.path.getsize(wav_path) / (16000 * 2)

            if duration < MIN_DURATION_SECONDS:
                st.warning(f"Your answer was only {int(duration)} seconds. Please speak for at least {MIN_DURATION_SECONDS} seconds.")
            else:
                with open(wav_path, "rb") as f:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f
                    )
                os.remove(wav_path)
                answer = transcript.text
                st.chat_message("user").markdown(answer)
                st.session_state.messages.append({"role": "user", "content": answer})
                st.session_state.answers.append(answer)
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
            final = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": final})
        st.session_state.final_feedback = final
