import streamlit as st
from openai import OpenAI
import tempfile
import os

# Setup page
st.title("🎙️ Voice-Based FANG Mock Interview")
st.write("Speak your answers to each question. After 5 questions, you’ll get detailed feedback and a final score.")

# Inputs
role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

MAX_QUESTIONS = 5

# OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Please add your OpenAI API key to `.streamlit/secrets.toml`")
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    def get_company_values(company_name):
        name = company_name.lower()
        if "amazon" in name:
            return "Amazon’s Leadership Principles such as Customer Obsession, Ownership, and Bias for Action"
        elif "google" in name:
            return "Google’s focus on innovation, scalability, and data-driven decision making"
        elif "meta" in name or "facebook" in name:
            return "Meta’s focus on impact, bold ideas, and rapid iteration"
        elif "netflix" in name:
            return "Netflix’s culture of freedom, responsibility, and excellence"
        elif "apple" in name:
            return "Apple’s emphasis on design, quality, and cross-functional collaboration"
        else:
            return "best practices from top-tier engineering companies"

    def system_prompt(role, company):
        values = get_company_values(company)
        return (
            f"You are a senior engineer at {company.title()} conducting a structured mock interview "
            f"for a candidate applying to a {role} position. Ask {MAX_QUESTIONS} questions, one at a time. "
            f"Do not give any feedback until the end. After all questions are answered, provide detailed feedback "
            f"and a final score out of 25."
        )

    # Initialize state
    if role and company:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
            st.session_state.question_index = 0
            st.session_state.answers = []
            st.session_state.awaiting_question = True
            st.session_state.final_feedback = None

        # Show chat history
        for msg in st.session_state.messages[1:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Ask next question
        if st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
            ask = f"Ask question #{st.session_state.question_index + 1}"
            st.session_state.messages.append({"role": "user", "content": ask})
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                question = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": question})
            st.session_state.awaiting_question = False

        # Upload audio response
        if not st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
            audio_file = st.file_uploader("🎤 Upload your answer (MP3/WAV)", type=["mp3", "wav"])
            if audio_file:
                with st.spinner("Transcribing your answer..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        tmp_file.write(audio_file.read())
                        tmp_path = tmp_file.name

                    with open(tmp_path, "rb") as f:
                        transcription = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=f
                        )

                    user_answer = transcription.text
                    os.remove(tmp_path)

                    st.session_state.messages.append({"role": "user", "content": user_answer})
                    with st.chat_message("user"):
                        st.markdown(user_answer)

                    st.session_state.answers.append(user_answer)
                    st.session_state.question_index += 1
                    st.session_state.awaiting_question = True

        # Final review
        if st.session_state.question_index == MAX_QUESTIONS and st.session_state.final_feedback is None:
            st.session_state.messages.append({
                "role": "user",
                "content": (
                    "The candidate has answered all questions. Please provide detailed feedback for each question, "
                    "a score out of 25, and an overall assessment of strengths and improvement areas."
                )
            })
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                feedback = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": feedback})
            st.session_state.final_feedback = feedback
