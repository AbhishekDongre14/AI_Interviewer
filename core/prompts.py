from langchain.prompts import PromptTemplate

def build_question_prompt(candidate_name: str, contact_info: str, experience: str, desired_position: str, tech_stack: str):
    template = (
        "You are an intelligent Hiring Assistant chatbot for 'TalentScout'.\n\n"
        "Candidate Name: {candidate_name}\n"
        "Contact Info: {contact_info}\n"
        "Experience: {experience}\n"
        "Desired Position: {desired_position}\n"
        "Tech Stack: {tech_stack}\n\n"
        "Generate **concise, technical interview questions** related to the tech stack above."
        " Return a numbered list with one question per line."
        " Focus on fundamentals, practical problem-solving, and a touch of system design where relevant."
    )
    return PromptTemplate(
        input_variables=[
            "candidate_name",
            "contact_info",
            "experience",
            "desired_position",
            "tech_stack",
        ],
        template=template,
    ).format(
        candidate_name=candidate_name,
        contact_info=contact_info,
        experience=experience,
        desired_position=desired_position,
        tech_stack=tech_stack,
    )

def build_eval_prompt():
    template = (
        "You are a strict but fair **technical interviewer**.\n"
        "Given a QUESTION and a CANDIDATE_ANSWER, provide: a short justification and a **score from 0 to 10**.\n"
        "Scoring rubric: 0=no relation, 3=partially correct with gaps, 6=mostly correct, 8=solid with detail, 10=excellent & precise.\n"
        "Output JSON exactly with keys: justification, score.\n\n"
        "QUESTION: {question}\n"
        "CANDIDATE_ANSWER: {answer}\n"
        "JSON:"
    )
    return PromptTemplate(input_variables=["question", "answer"], template=template)