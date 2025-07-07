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
role = st.text_input("🧑‍💻 Target Role", placeholder="e.g., Software Engineer")
company = st.text_input("🏢 Target Company", placeholder="e.g., Amazon")

# Ensure secrets are configured
if "openai_api_key" not in st.secrets:
    st.error("Missing OpenAI API key. Please add it to your Streamlit secrets.", icon="🚫")
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

    def get_prompt(role: str, company: str) -> str:
        company_lower = company.lower()
        if "amazon" in company_lower:
            values = "Amazon’s Leadership Principles such as Customer Obsession, Ownership, and Bias for Action"
        elif "google" in company_lower:
            values = "Google’s focus on innovation, scalability, and data-driven engineering"
        elif "meta" in company_lower or "facebook" in company_lower:
            values = "Meta's emphasis on impact, moving fast, and bold decision making"
        elif "netflix" in company_lower:
            values = "Netflix’s culture of freedom, responsibility, and high performance"
        elif "apple" in company_lower:
            values = "Apple’s attention to detail, cross-functional collaboration, and product excellence"
        else:
            values = "best practices from top-tier engineering organizations"

        return (
            f"You are a senior engineer at {company.title()} conducting a mock interview for a candidate applying for a {role} role. "
            f"Tailor your questions based on {values}. Ask a mix of technical and behavioral questions, "
            "probe deeper with realistic follow-ups, and simulate an authentic FANG-style interview process. "
            "After each candidate response, provide a score (1-5) and detailed feedback to help them improve."
        )

    # Start the interview automatically when role and company are filled
    if role and company:
        if "messages" not in st.session_state:
            # Initialize system and assistant messages
            st.session_state.messages = [
                {"role": "system", "content": get_prompt(role, company)},
                {"role": "assistant", "content": (
                    f"👋 Hi! Welcome to your mock interview for the **{role}** role at **{company.title()}**.\n\n"
                    "Let’s get started. First question:\n\n"
                    "Tell me about a time when you had to make a tough technical decision under time pressure. What was the context, and how did you approach it?"
                )}
            ]

    # Display previous messages
    if "messages" in st.session_state:
        for msg in st.session_state.messages[1:]:  # Skip the system prompt
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # User input
        if user_input := st.chat_input("Your response..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            # Assistant response
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
