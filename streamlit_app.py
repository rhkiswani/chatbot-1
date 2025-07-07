import streamlit as st
from openai import OpenAI

# Set page title
st.title("🧠 FANG-Style Structured Mock Interview")

st.write(
    "This app simulates a structured mock interview for top tech companies (e.g., Google, Meta, Amazon). "
    "After 5 questions, you'll receive a final score and feedback summary based on your answers."
)

# Input fields
role = st.text_input("Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("Target Company", placeholder="e.g., Google")

# Constants
MAX_QUESTIONS = 5

# OpenAI setup
if "openai_api_key" not in st.secrets:
    st.error("Missing OpenAI API key. Please add it to your Streamlit secrets.")
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
            return "industry best practices from top-tier engineering companies"

    def system_prompt(role, company):
        values = get_company_values(company)
        return (
            f"You are a senior engineer at {company.title()} conducting a structured mock interview "
            f"for a candidate applying to a {role} position. The interview should include {MAX_QUESTIONS} questions: "
            "a mix of technical and behavioral. For each answer, provide a score from 1–5 and detailed feedback. "
            "Ask only one question at a time. After all questions are answered, give a final rating with summary feedback."
        )

    # Initialize session state
    if role and company:
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {"role": "system", "content": system_prompt(role, company)}
            ]
            st.session_state.question_count = 0
            st.session_state.feedback = []

        # Display existing conversation
        for msg in st.session_state.messages[1:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # If waiting for a new question and under limit
        if st.session_state.question_count < MAX_QUESTIONS and (
            len(st.session_state.messages) == 1 or st.session_state.messages[-1]["role"] != "assistant"
        ):
            # Ask next interview question
            question_request = (
                f"Ask question #{st.session_state.question_count + 1} for the {role} role at {company}."
            )
            st.session_state.messages.append({"role": "user", "content": question_request})
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})

        # User input: candidate's answer
        if user_input := st.chat_input("Your answer..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Get feedback and score for that answer
            feedback_prompt = (
                "Please evaluate the candidate's response. Give a score (1–5) and detailed feedback."
            )
            st.session_state.messages.append({"role": "user", "content": feedback_prompt})
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                feedback = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": feedback})

            # Store feedback summary
            st.session_state.feedback.append(feedback)
            st.session_state.question_count += 1

        # After all questions are answered
        if st.session_state.question_count == MAX_QUESTIONS:
            if "final_score_given" not in st.session_state:
                st.session_state.messages.append({
                    "role": "user",
                    "content": (
                        "Now that the candidate answered all questions, give a final score (out of 25) "
                        "and provide an overall summary of strengths and areas for improvement."
                    )
                })
                stream = client.chat.completions.create(
                    model="gpt-4",
                    messages=st.session_state.messages,
                    stream=True,
                )
                with st.chat_message("assistant"):
                    final_summary = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": final_summary})
                st.session_state.final_score_given = True
