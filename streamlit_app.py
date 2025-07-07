import streamlit as st
from openai import OpenAI

# App title and description
st.title("🎯 FANG-Style Mock Interviewer")
st.write(
    "This is an AI-powered mock interviewer simulating a senior engineer from top-tier tech companies "
    "(e.g., Amazon, Google, Meta). It tailors questions based on your target **role** and **company**, "
    "asks follow-ups, and provides rankings and feedback."
)

# Inputs for customization
role = st.text_input("🧑‍💻 Target Role (e.g., Backend Engineer, TPM)", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company (e.g., Amazon, Google)", placeholder="e.g., Meta")

# Ensure secrets are configured
if "openai_api_key" not in st.secrets:
    st.error("Missing OpenAI API key. Please add it to your Streamlit secrets.", icon="🚫")
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    # Generate dynamic system prompt based on inputs
    def get_prompt(role: str, company: str) -> str:
        company = company.lower()
        if "amazon" in company:
            values = "Amazon’s Leadership Principles such as Customer Obsession, Ownership, and Bias for Action"
        elif "google" in company:
            values = "Google’s focus on innovation, scalability, and data-driven engineering"
        elif "meta" in company or "facebook" in company:
            values = "Meta's emphasis on impact, move fast, and be bold culture"
        elif "netflix" in company:
            values = "Netflix’s culture of freedom, responsibility, and high performance"
        elif "apple" in company:
            values = "Apple’s attention to detail, cross-functional collaboration, and product excellence"
        else:
            values = "best practices from top-tier engineering organizations"

        return (
            f"You are a senior engineer at {company.title()} conducting a mock interview for a candidate applying for a {role} role. "
            f"Tailor your questions based on {values}. Ask a mix of technical and behavioral questions, "
            "probe deeper with realistic follow-ups, and simulate an authentic FANG-style interview process. "
            "After each candidate response, provide a score (1-5) and detailed feedback to help them improve."
        )

    # Initialize session
    if "messages" not in st.session_state and role and company:
        st.session_state.messages = [
            {"role": "system", "content": get_prompt(role, company)}
        ]

    # Display conversation
    if "messages" in st.session_state:
        for msg in st.session_state.messages[1:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if user_input := st.chat_input("Type your response or ask to start the interview..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Generate assistant response
            stream = client.chat.completions.create(
                model="gpt-4",
                messages=st.session_state.messages,
                stream=True,
            )
            with st.chat_message("assistant"):
                response = st.write_stream(stream)
            st.session_state.messages.append({"role": "assistant", "content": response})
    else:
        st.info("Please enter your target role and company above to begin.")
