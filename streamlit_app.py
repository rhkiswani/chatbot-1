import streamlit as st
from openai import OpenAI

# Page setup
st.title("🧠 FANG-Style Mock Interview (Structured)")
st.write(
    "Simulates a real interview for top companies. You’ll get 5 tailored questions for your role and company, "
    "then receive detailed feedback and scoring at the end."
)

# Input fields
role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

# Constants
MAX_QUESTIONS = 5

# OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Please add your OpenAI API key to `.streamlit/secrets.toml`", icon="🔑")
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
            f"for a candidate applying to a {role} position. The interview should consist of {MAX_QUESTIONS} questions: "
            f"a mix of technical and behavioral. Ask one question at a time. Wait for the answer before asking the next. "
            f"Do not give any feedback or scores until the end. After all answers are collected, give detailed feedback and "
            f"a final rating (score out of 25), broken down by question."
        )

    # Initialize state
    if role and company:
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
            st.session_state.question_index = 0
            st.session_state.answers = []
            st.session_state.awaiting_question = True
            st.session_state.final_feedback = None

        # Show past conversation (except system prompt)
        for msg in st.session_state.messages[1:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Ask a question if needed
        if st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
            question_prompt = f"Ask question #{st.session_state.question_index + 1} for the candidate."
            st.session_state.messages.append({"role": "user", "content": question_prompt})
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.awaiting_question = False

        # Accept user input
        if not st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
            if user_input := st.chat_input("Your answer..."):
                st.session_state.messages.append({"role": "user", "content": user_input})
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state.answers.append(user_input)
                st.session_state.question_index += 1
                st.session_state.awaiting_question = True

        # If all questions are answered, generate final feedback
        if st.session_state.question_index == MAX_QUESTIONS and st.session_state.final_feedback is None:
            st.session_state.messages.append({
                "role": "user",
                "content": (
                    "Now that the candidate has answered all questions, please evaluate their performance. "
                    "Provide a score out of 25 (5 per question) and a detailed summary of strengths and areas to improve."
                )
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
