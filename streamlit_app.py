import streamlit as st
from openai import OpenAI

st.title("💬 FANG Mock Interview")

role = st.text_input("🎯 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Google")

MAX_QUESTIONS = 5

if "openai_api_key" not in st.secrets:
    st.error("Add your OpenAI API key to `.streamlit/secrets.toml`")
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

if role and company:
    st.markdown(f"### Welcome to your {role} mock interview at {company}! 🎉")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": system_prompt(role, company)}]
        st.session_state.question_index = 0
        st.session_state.answers = []
        st.session_state.awaiting_question = True
        st.session_state.final_feedback = None

    # Display all chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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

    # Show answer form only if waiting for answer and questions remain
    if not st.session_state.awaiting_question and st.session_state.question_index < MAX_QUESTIONS:
        input_key = f"answer_input_{st.session_state.question_index}"

        # Initialize input key only once
        if input_key not in st.session_state:
            st.session_state[input_key] = ""

        with st.form(key="answer_form", clear_on_submit=True):
            answer = st.text_input("Your answer:", key=input_key)
            submitted = st.form_submit_button("Submit answer")

        if submitted and st.session_state[input_key].strip():
            user_answer = st.session_state[input_key].strip()
            st.session_state.messages.append({"role": "user", "content": user_answer})
            st.session_state.answers.append(user_answer)
            st.session_state.question_index += 1
            st.session_state.awaiting_question = True

            st.experimental_rerun()

    # After all questions answered, generate feedback once
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
