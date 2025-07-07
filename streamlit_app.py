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
