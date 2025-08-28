import os
import json
import re
import time
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from core.llm import get_interviewer_lm, get_evaluator_lm
from core.prompts import build_question_prompt, build_eval_prompt
from core.validators import is_valid_email, parse_and_validate_tech_stack, is_nonempty_string
from core.storage import (
    ensure_data_dirs,
    upsert_candidate,
    append_performance,
    save_chat_history,
)
from core.evaluator import grade_qa_batch
from core.flow import (
    Phase,
    next_basic_field,
    BASIC_FIELDS,
    ensure_session_state,
    prepare_questions,
)

# Streamlit page config
st.set_page_config(page_title="TalentScout — LLM Interviewer", page_icon="🧠", layout="centered")

# Make sure data directories exist
ensure_data_dirs()

# Initialize session state
ensure_session_state()

# ✅ New state for locking chat
if "chat_locked" not in st.session_state:
    st.session_state.chat_locked = False

# ✅ New state for question generation
if "generating_questions" not in st.session_state:
    st.session_state.generating_questions = False
# ✅ New state to track if we're processing the final answer
if "processing_final_answer" not in st.session_state:
    st.session_state.processing_final_answer = False
st.title("🎯 TalentScout — AI Interviewer")
st.caption("Tech interview simulation with automated scoring. Your responses are stored locally by the interviewer.")

# Helper to emit chat messages
def bot(msg: str):
    with st.chat_message("assistant"):
        st.markdown(msg)

def user(msg: str):
    with st.chat_message("user"):
        st.markdown(msg)

# Phases
phase: str = st.session_state.phase

# Sidebar with enhanced styling
with st.sidebar:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem; border-radius: 1rem; margin-bottom: 1rem;'>
        <h3 style='color: white; margin: 0; text-align: center;'>📊 Interview Status</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Status indicators with better formatting
    status_color = {
        Phase.GREET: "#ffa726",
        Phase.WAIT_GREETING: "#ffa726", 
        Phase.COLLECT_INFO: "#42a5f5",
        Phase.INTERVIEW: "#66bb6a",
        Phase.SCORING: "#ab47bc",
        Phase.THANK_YOU: "#26c6da"
    }.get(phase, "#9e9e9e")
    
    st.markdown(f"""
    <div style='background: {status_color}15; border: 2px solid {status_color}; border-radius: 0.5rem; padding: 1rem; margin: 1rem 0;'>
        <div style='color: {status_color}; font-weight: 600; font-size: 0.9rem;'>CURRENT PHASE</div>
        <div style='font-size: 1.1rem; font-weight: 700; margin-top: 0.25rem;'>{phase.replace('_', ' ').title()}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.candidate.get('id'):
        st.markdown("**👤 Candidate Details**")
        if st.session_state.candidate.get("name"):
            st.markdown(f"**Name:** {st.session_state.candidate['name']}")
        if st.session_state.candidate.get("email"):
            st.markdown(f"**Email:** {st.session_state.candidate['email']}")
        if st.session_state.candidate.get("desired_position"):
            st.markdown(f"**Role:** {st.session_state.candidate['desired_position']}")
        if st.session_state.candidate.get("tech_stack"):
            st.markdown(f"**Tech:** {st.session_state.candidate['tech_stack']}")
    
    # Progress indicator for interview phase
    if st.session_state.phase == Phase.INTERVIEW and hasattr(st.session_state, 'current_q'):
        progress = (st.session_state.current_q + 1) / 10
        st.markdown("**📝 Interview Progress**")
        st.progress(progress)
        st.markdown(f"Question {st.session_state.current_q + 1} of 10")
    elif st.session_state.phase == Phase.COLLECT_INFO and hasattr(st.session_state, 'pending_field'):
        fields_order = ["name", "email", "experience", "desired_position", "tech_stack"]
        if st.session_state.pending_field in fields_order:
            progress = fields_order.index(st.session_state.pending_field) / len(fields_order)
            st.markdown("**📋 Info Collection Progress**")
            st.progress(progress)
            st.markdown(f"Step {fields_order.index(st.session_state.pending_field) + 1} of {len(fields_order)}")

# First-time greeting with enhanced styling
if phase == Phase.GREET:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 2rem; border-radius: 1rem; margin: 2rem 0;'>
        <div style='text-align: center;'>
            <div style='font-size: 3rem; margin-bottom: 1rem;'>👋</div>
            <h2 style='color: #2d3748; margin-bottom: 1rem;'>Welcome to TalentScout!</h2>
            <p style='color: #4a5568; font-size: 1.1rem; line-height: 1.6;'>
                I'm your <strong>AI Interview Assistant</strong>. Here's how our session will work:
            </p>
        </div>
        <div style='background: white; border-radius: 0.75rem; padding: 1.5rem; margin-top: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);'>
            <div style='display: grid; gap: 1rem;'>
                <div style='display: flex; align-items: center; gap: 1rem;'>
                    <div style='background: #4299e1; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-weight: bold;'>1</div>
                    <div><strong>Greeting:</strong> Say <em>hi/hello</em> to begin our conversation</div>
                </div>
                <div style='display: flex; align-items: center; gap: 1rem;'>
                    <div style='background: #48bb78; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-weight: bold;'>2</div>
                    <div><strong>Details:</strong> Share your basic info (name, email, experience, role, tech stack)</div>
                </div>
                <div style='display: flex; align-items: center; gap: 1rem;'>
                    <div style='background: #ed8936; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-weight: bold;'>3</div>
                    <div><strong>Interview:</strong> Answer 10 technical questions tailored to your expertise</div>
                </div>
                <div style='display: flex; align-items: center; gap: 1rem;'>
                    <div style='background: #9f7aea; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-weight: bold;'>4</div>
                    <div><strong>Results:</strong> Get your performance score out of 100 with detailed feedback</div>
                </div>
            </div>
        </div>
        <div style='text-align: center; margin-top: 1.5rem;'>
            <p style='color: #718096; font-size: 0.9rem;'>
                <strong>Note:</strong> All responses are stored locally for hiring team review
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.session_state.phase = Phase.WAIT_GREETING

# ---------- Chat rendering & locking ----------
# Show loading state during question generation
if st.session_state.generating_questions:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; border-radius: 1rem; text-align: center; margin: 2rem 0;'>
        <div style='color: white; font-size: 1.5rem; margin-bottom: 1rem;'>
            🤖 AI is crafting your personalized interview questions...
        </div>
        <div style='color: rgba(255,255,255,0.8); font-size: 1rem; margin-bottom: 1.5rem;'>
            This may take 10-15 seconds. Please wait while I analyze your tech stack and experience.
        </div>
        <div style='display: flex; justify-content: center; align-items: center; gap: 0.5rem;'>
            <div style='width: 12px; height: 12px; background: white; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both;'></div>
            <div style='width: 12px; height: 12px; background: white; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both; animation-delay: -0.16s;'></div>
            <div style='width: 12px; height: 12px; background: white; border-radius: 50%; animation: bounce 1.4s ease-in-out infinite both; animation-delay: -0.32s;'></div>
        </div>
    </div>
    <style>
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
    """, unsafe_allow_html=True)

# Show chat history with enhanced styling
for role, content in st.session_state.chat_history:
    if role == "assistant":
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); padding: 1rem; border-radius: 1rem; margin: 1rem 0; border-left: 4px solid #2196f3;'>
            <div style='display: flex; align-items: flex-start; gap: 0.75rem;'>
                <div style='background: #2196f3; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; flex-shrink: 0;'>🤖</div>
                <div style='flex: 1; line-height: 1.6; color: black;'>{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #e8f5e8 0%, #f0f8ff 100%); padding: 1rem; border-radius: 1rem; margin: 1rem 0; border-left: 4px solid #4caf50; margin-left: 2rem;'>
            <div style='display: flex; align-items: flex-start; gap: 0.75rem;'>
                <div style='background: #4caf50; color: white; border-radius: 50%; width: 2rem; height: 2rem; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; flex-shrink: 0;'>👤</div>
                <div style='flex: 1; line-height: 1.6; color: black;'>{content}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# Chat input logic - disable during question generation and after 10th question
if st.session_state.generating_questions:
    prompt = None
    st.info("⏳ Please wait, processing your information...")
elif st.session_state.phase == Phase.THANK_YOU:
    prompt = None
elif st.session_state.phase == Phase.SCORING:
    prompt = None
else:
    prompt = st.chat_input("Type your response here... 💬")

# ---------- Input processing protection ----------
# Only process if we have a valid prompt and we're not in a locked state during critical operations
if prompt is not None and prompt.strip():
    # Check if we should ignore the input due to race conditions
    should_process = True
    
    if st.session_state.phase == Phase.SCORING and not st.session_state.processing_final_answer:
        st.warning("Your message was received while the system was processing and has been ignored.")
        should_process = False
    
    if should_process:
        user(prompt)
        st.session_state.chat_history.append(("user", prompt))

    # Lock chat immediately (except when processing final answer)
    if not st.session_state.processing_final_answer:
        st.session_state.chat_locked = True

    # ---------- Handle greeting ----------
    if st.session_state.phase == Phase.WAIT_GREETING:
        if re.search(r"\b(hi|hii|hie|hello|hey|howdy|yo)\b", prompt.strip().lower()):
            bot("Great! Let's capture your basic details one by one. First, **what's your full name?**")
            st.session_state.chat_history.append(("assistant", "Great! Let's capture your basic details one by one. First, **what's your full name?**"))
            st.session_state.phase = Phase.COLLECT_INFO
            st.session_state.pending_field = "name"
        else:
            bot("Please greet to begin — try saying **hello** 👋")
            st.session_state.chat_history.append(("assistant", "Please greet to begin — try saying **hello** 👋"))
            st.session_state.chat_locked = False

    # ---------- Collect info ----------
    elif st.session_state.phase == Phase.COLLECT_INFO:
        field = st.session_state.pending_field
        value = prompt.strip()
        valid = False
        err = None

        if field == "name":
            valid = is_nonempty_string(value) and len(value.split()) >= 2
            if not valid:
                err = "Please provide your **full name** (first and last)."
        elif field == "email":
            valid = is_valid_email(value)
            if not valid:
                err = "Please provide a **valid email** (e.g., name@gmail.com)."
        elif field == "experience":
            valid = is_nonempty_string(value)
            if not valid:
                err = "Please specify your **experience** (e.g., '3 years')."
        elif field == "desired_position":
            valid = is_nonempty_string(value)
            if not valid:
                err = "Please provide the **desired position** (e.g., 'Backend Developer')."
        elif field == "tech_stack":
            tech_list, tech_err = parse_and_validate_tech_stack(value)
            valid = tech_err is None and len(tech_list) > 0
            if not valid:
                err = tech_err or "Please provide a comma-separated **tech stack** (e.g., 'Python, Django, REST')."
            else:
                st.session_state.candidate["tech_list"] = tech_list

        if not valid:
            bot(err)
            st.session_state.chat_history.append(("assistant", err))
            st.session_state.chat_locked = False
        else:
            st.session_state.candidate[field] = value
            nxt = next_basic_field(field)
            if nxt is None:
                st.session_state.candidate["id"] = st.session_state.candidate.get("id") or (
                    datetime.utcnow().strftime("%Y%m%d%H%M%S")
                )
                upsert_candidate(st.session_state.candidate)

                interviewer = get_interviewer_lm()
                q_prompt = build_question_prompt(
                    candidate_name=st.session_state.candidate["name"],
                    contact_info=st.session_state.candidate["email"],
                    experience=st.session_state.candidate["experience"],
                    desired_position=st.session_state.candidate["desired_position"],
                    tech_stack=st.session_state.candidate["tech_stack"],
                )

                with st.spinner("Generating interview questions… ⏳"):
                    questions = prepare_questions(interviewer, q_prompt, st.session_state.candidate["tech_list"], total=10)

                st.session_state.questions = questions
                st.session_state.phase = Phase.INTERVIEW
                first_q = f"Question 1/10: {questions[0]}"
                bot("Thanks! Your details are recorded. Let's begin the interview.")
                st.session_state.chat_history.append(("assistant", "Thanks! Your details are recorded. Let's begin the interview."))
                bot(first_q)
                st.session_state.chat_history.append(("assistant", first_q))
                st.session_state.current_q = 0
                save_chat_history(st.session_state.candidate["id"], st.session_state.chat_history)
                st.session_state.chat_locked = False
            else:
                st.session_state.pending_field = nxt
                label = {
                    "email": "Great, now your **email**?",
                    "experience": "Thanks! What's your **work experience** (e.g., '3 years')?",
                    "desired_position": "Which **position** are you aiming for?",
                    "tech_stack": "Finally, list your **tech stack** (comma-separated).",
                }[nxt]
                bot(label)
                st.session_state.chat_history.append(("assistant", label))
                st.session_state.chat_locked = False

    # ---------- Interview Q&A ----------
    elif st.session_state.phase == Phase.INTERVIEW:
        idx = st.session_state.current_q
        q = st.session_state.questions[idx]
        st.session_state.answers.append({"q": q, "a": prompt})

        if idx < len(st.session_state.questions) - 1:
            # Not the last question - continue as normal
            st.session_state.current_q += 1
            next_q = st.session_state.questions[st.session_state.current_q]
            msg = f"Question {st.session_state.current_q + 1}/10: {next_q}"
            bot(msg)
            st.session_state.chat_history.append(("assistant", msg))
            save_chat_history(st.session_state.candidate["id"], st.session_state.chat_history)
            st.session_state.chat_locked = False
        else:
            # This is the 10th question response - handle it differently
            st.session_state.processing_final_answer = True
            
            # Show completion message but don't change phase yet
            bot("Thanks for completing all questions. Evaluating your responses… ⏳")
            st.session_state.chat_history.append(("assistant", "Thanks for completing all questions. Evaluating your responses… ⏳"))
            
            # Save chat history before starting evaluation
            save_chat_history(st.session_state.candidate["id"], st.session_state.chat_history)
            
            # Now proceed with scoring
            st.session_state.phase = Phase.SCORING

            with st.spinner("Scoring your answers…"):
                evaluator = get_evaluator_lm()
                eval_prompt = build_eval_prompt()
                results = grade_qa_batch(evaluator, eval_prompt, st.session_state.answers)

                total_score = max(0, min(100, int(round(sum(r.get("score", 0) for r in results)))))
                st.session_state.performance = {"total": total_score, "breakdown": results}

                append_performance(
                    candidate_id=st.session_state.candidate["id"],
                    name=st.session_state.candidate["name"],
                    email=st.session_state.candidate["email"],
                    role=st.session_state.candidate["desired_position"],
                    tech_stack=st.session_state.candidate["tech_stack"],
                    score=total_score,
                    breakdown_json=json.dumps(results, ensure_ascii=False),
                )
                save_chat_history(st.session_state.candidate["id"], st.session_state.chat_history)

            st.session_state.phase = Phase.THANK_YOU
            st.session_state.processing_final_answer = False
            st.rerun()

    # Persist chat
    if st.session_state.candidate.get("id"):
        save_chat_history(st.session_state.candidate["id"], st.session_state.chat_history)

# ---------- Final Thank-you page with enhanced styling ----------
if st.session_state.phase == Phase.THANK_YOU:
    score = st.session_state.performance["total"]
    
    # Animated header
    st.markdown("""
    <div style='text-align: center; margin: 2rem 0;'>
        <div style='font-size: 4rem; margin-bottom: 1rem;'>🎉</div>
        <h1 style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem; margin: 0;'>
            Interview Complete!
        </h1>
        <p style='color: #6b7280; font-size: 1.2rem; margin-top: 0.5rem;'>
            Thank you for your time and effort
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Animated score display
    ph = st.empty()
    for i in range(0, score + 1):
        # Determine color based on score
        if i >= 80:
            color = "#10b981"  # Green
            grade = "Excellent"
        elif i >= 70:
            color = "#3b82f6"  # Blue  
            grade = "Good"
        elif i >= 60:
            color = "#f59e0b"  # Yellow
            grade = "Average"
        else:
            color = "#ef4444"  # Red
            grade = "Needs Improvement"
            
        ph.markdown(f"""
        <div style='text-align:center; background: linear-gradient(135deg, {color}15 0%, {color}25 100%); padding: 3rem; border-radius: 1.5rem; margin: 2rem 0; border: 2px solid {color};'>
            <div style='font-size: 5rem; font-weight: 800; color: {color}; margin-bottom: 0.5rem;'>🏆 {i}</div>
            <div style='font-size: 1.5rem; color: #374151; font-weight: 600; margin-bottom: 0.25rem;'>Out of 100</div>
            <div style='font-size: 1.1rem; color: {color}; font-weight: 600;'>{grade if i == score else ""}</div>
        </div>
        """, unsafe_allow_html=True)
        time.sleep(0.03)

    # Progress bar with custom styling
    st.markdown("""
    <div style='margin: 2rem 0;'>
        <div style='font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; text-align: center;'>Performance Score</div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(score / 100.0)
    
    # Performance breakdown if available
    if "breakdown" in st.session_state.performance:
        with st.expander("📊 Detailed Performance Breakdown", expanded=False):
            breakdown = st.session_state.performance["breakdown"]
            for i, result in enumerate(breakdown):
                q_score = result.get("score", 0)
                st.markdown(f"""
                **Question {i+1}:** {q_score}/10 points
                """)

    # Final message
    st.markdown("""
    <div style='background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 2rem; border-radius: 1rem; margin: 2rem 0; text-align: center; border: 2px solid #f59e0b;'>
        <div style='font-size: 1.3rem; font-weight: 600; color: #92400e; margin-bottom: 1rem;'>
            🔒 Interview Session Completed
        </div>
        <p style='color: #78350f; margin: 0; line-height: 1.6;'>
            Your responses have been saved and will be reviewed by our hiring team.<br>
            You may now close this tab or refresh the page to start a new interview.
        </p>
    </div>
    """, unsafe_allow_html=True)