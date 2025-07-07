import streamlit as st
from openai import OpenAI
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import av
import numpy as np
import tempfile
import os
import wave
import queue

# Constants
MAX_QUESTIONS = 5
audio_q = queue.Queue()

# UI setup
st.title("🎤 FANG Mock Interview (Live Voice)")
st.write("Answer questions with your voice. The app will transcribe your responses using OpenAI Whisper.")

role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

# Whisper + OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Add your OpenAI API key to `.streamlit/secrets.toml`")
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
        st.success(f"Welcome! Starting your {role} mock interview for {company}. 🎙️")
        
        # Initialize session
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
            st.session_state.question_index = 0
            st.session_state.answers = []
            st.session_state.awaiting_question = True
            st.session_state.final_feedback = None
            st.session_state.audio_recording = None

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

        # AudioProcessor for live mic capture
        class AudioProcessor(AudioProcessorBase):
            def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
                audio = frame.to_ndarray().flatten().astype(np.int16).tobytes()
                audio_q.put(audio)
                return frame

        # Start mic
        webrtc_ctx = webrtc_streamer(
            key="voice-interview",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=1024,
            audio_processor_factory=AudioProcessor,
            media_stream_constraints={"audio": True, "video": False},
        )

        # Voice recording and transcription
        def record_and_transcribe():
            st.session_state.audio_recording = b""
            while webrtc_ctx.state.playing:
                try:
                    audio_chunk = audio_q.get(timeout=5)
                    st.session_state.audio_recording += audio_chunk
                except queue.Empty:
                    break

            # Save valid .wav using wave module
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                with wave.open(tmp, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)
                    wf.writeframes(st.session_state.audio_recording)
                tmp_path = tmp.name

            # Transcribe
            with open(tmp_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            os.remove(tmp_path)
            return transcript.text

        # Submit voice answer
        if st.button("✅ Submit Voice Answer"):
            with st.spinner("Processing your voice..."):
                result_text = record_and_transcribe()
                st.session_state.messages.append({"role": "user", "content": result_text})
                with st.chat_message("user"):
                    st.markdown(result_text)

                st.session_state.answers.append(result_text)
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
