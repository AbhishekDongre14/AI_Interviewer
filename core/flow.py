import re
from typing import List

# Add the missing BASIC_FIELDS constant
BASIC_FIELDS = ["name", "email", "experience", "desired_position", "tech_stack"]

class Phase:
    GREET = "greet"
    WAIT_GREETING = "wait_greeting"
    COLLECT_INFO = "collect_info"
    INTERVIEW = "interview"
    SCORING = "scoring"
    THANK_YOU = "thankyou"

def ensure_session_state():
    import streamlit as st
    if "phase" not in st.session_state:
        st.session_state.phase = Phase.GREET
    st.session_state.setdefault("pending_field", None)
    st.session_state.setdefault("candidate", {})
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("current_q", 0)
    st.session_state.setdefault("answers", [])
    st.session_state.setdefault("chat_history", [])

def next_basic_field(current_field: str | None):
    if current_field is None:
        return BASIC_FIELDS[0]
    try:
        idx = BASIC_FIELDS.index(current_field)
    except ValueError:
        return BASIC_FIELDS[0]
    if idx == len(BASIC_FIELDS) - 1:
        return None
    return BASIC_FIELDS[idx + 1]

def parse_numbered_list(text: str) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out = []
    for l in lines:
        # Accept formats like: "1. question", "1) question", "- question"
        l = re.sub(r"^(?:\d+[\).]|[-*])\s*", "", l)
        if len(l) > 3:
            out.append(l)
    return out

def prepare_questions(interviewer_llm, question_prompt_text: str, tech_list: List[str], total: int = 10) -> List[str]:
    resp = interviewer_llm.invoke(question_prompt_text)
    content = resp.content if hasattr(resp, "content") else str(resp)
    all_qs = parse_numbered_list(content)
    
    # Ensure coverage across tech_list. If insufficient, synthesize per-tech ask.
    qs: List[str] = []
    per_tech = max(1, total // max(1, len(tech_list)))
    
    # First pass: take up to total questions from generated
    for q in all_qs[: total]:
        qs.append(q)
    
    # If not enough, top up per tech
    i = 0
    while len(qs) < total:
        tech = tech_list[i % len(tech_list)]
        qs.append(f"In {tech}, explain a concept or solve a small problem relevant to {tech} fundamentals.")
        i += 1
    
    # Trim to exact total
    return qs[: total]