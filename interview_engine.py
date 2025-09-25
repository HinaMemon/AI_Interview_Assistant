# interview_engine.py
"""
Interview engine that uses Google Gemini (via google-generativeai) to:
 - generate multiple interview questions for a given job title
 - give student-friendly, step-by-step feedback on an answer

Provides:
 - generate_questions(job_title, n_questions=10) -> list[str]
 - get_feedback_on_answer(question, answer) -> str (multiline feedback)
 - InterviewSession(job_title, n_questions=10) -> stateful iterator with next_question()

If Gemini is not available (no package or no API key), the module falls back
to safe dummy questions/feedback so the UI does not crash.
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# Try to import google.generativeai; if missing we fallback
try:
    import google.generativeai as genai  # type: ignore
    HAVE_GENAI = True
except Exception:
    HAVE_GENAI = False

# Load .env
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
MODEL_NAME = "gemini-1.5-flash"  # good default for balance of speed & quality

# Configure model if available
MODEL = None
if HAVE_GENAI and GEMINI_KEY:
    try:
        genai.configure(api_key=GEMINI_KEY)
        MODEL = genai.GenerativeModel(MODEL_NAME)
    except Exception:
        MODEL = None


# ----------------- Fallback data (safe) -----------------
FALLBACK_QUESTIONS = [
    "Why should we hire you?",
    "Tell me about yourself.",
    "What are your strengths?",
    "What are your weaknesses?",
    "Where do you see yourself in 5 years?",
    "Why do you want to work here?",
    "Tell me about a challenge you faced at work.",
    "How do you handle pressure?",
    "What motivates you?",
    "Do you have any questions for us?"
]


# ----------------- Utility parsing helpers -----------------
def _clean_list_from_text(text: str) -> List[str]:
    """
    Take multiline text and return a cleaned list of lines (remove leading numbers/ bullets).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = []
    for ln in lines:
        # remove leading numbering or bullets: "1. ", "1) ", "- ", "* "
        while ln and (ln[0].isdigit() or ln[0] in "-*"):
            # strip leading digits and common punctuation
            ln = ln.lstrip("0123456789. )-*\t")
            ln = ln.strip()
        if ln:
            cleaned.append(ln)
    return cleaned


# ----------------- Public functions -----------------
def generate_questions(job_title: str, n_questions: int = 10) -> List[str]:
    """
    Return a list of interview questions for the provided job_title.
    If Gemini is available and configured, call it; otherwise return fallback questions.
    """
    if not job_title:
        return ["Please provide a job title."]

    if MODEL is None:
        # fallback: return first n from constant list (or repeat with small variations)
        return FALLBACK_QUESTIONS[:n_questions]

    prompt = (
        f"You are an expert interview coach. Generate {n_questions} clear, concise interview "
        f"questions for a candidate applying for the role: \"{job_title}\". "
        "Return a numbered list, one question per line. Do not add extra commentary."
    )

    try:
        resp = MODEL.generate_content(prompt)
        text = (resp.text or "").strip()
        questions = _clean_list_from_text(text)
        # If returned fewer than requested, pad with fallback questions
        if len(questions) < n_questions:
            questions += [q for q in FALLBACK_QUESTIONS if q not in questions]
            questions = questions[:n_questions]
        return questions[:n_questions]
    except Exception as e:
        # graceful fallback on any error
        return [f"Error generating questions: {e}"] + FALLBACK_QUESTIONS[: max(0, n_questions-1)]


def get_feedback_on_answer(question: str, answer: str) -> str:
    """
    Return student-friendly step-by-step feedback for a given question & answer.
    Output is a multi-line string where each line is a short step or bullet.
    If Gemini unavailable, returns a simple heuristic feedback.
    """
    if not answer or not answer.strip():
        return "No answer provided. Please write your response before requesting feedback."

    if MODEL is None:
        # Simple fallback feedback in easy wording
        ans_len = len(answer.strip())
        feedback_lines = []
        if ans_len < 30:
            feedback_lines.append("1) Score: 40/100")
            feedback_lines.append("2) Strength: You tried to answer quickly.")
            feedback_lines.append("3) Improve: Add one concrete example (what you did).")
            feedback_lines.append("4) Improve: Add the result (what changed because of your action).")
            feedback_lines.append("5) Model answer (example): I led X project where I did Y and achieved Z.")
        else:
            feedback_lines.append("1) Score: 75/100")
            feedback_lines.append("2) Strength: Clear structure and some example included.")
            feedback_lines.append("3) Improve: Be more specific about numbers or results.")
            feedback_lines.append("4) Improve: Add one short sentence about learning from the experience.")
            feedback_lines.append("5) Model answer (example): I improved X by doing Y which increased Z by 20%.")
        return "\n".join(feedback_lines)

    # Use Gemini to generate step-by-step feedback in simple language
    prompt = f"""
You are an interview coach giving feedback to a student. Use very simple, short sentences
(so a student can easily understand). The question is:
{question}

The candidate's answer is:
{answer}

Provide feedback as a short numbered list with these parts:
1) A short score out of 100.
2) Two short strengths (one sentence each).
3) Three short, actionable improvements (one sentence each).
4) A single short model answer (1-2 sentences).

Use plain, easy words. Keep each item concise (<= 20 words). Return only the numbered list, one item per line.
"""
    try:
        resp = MODEL.generate_content(prompt)
        text = (resp.text or "").strip()
        # Clean lines and ensure readability
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return "No feedback returned. Try again."
        # If lines not numbered, attempt to split into short sentences
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating feedback: {e}"


# ----------------- Stateful helper: InterviewSession -----------------
class InterviewSession:
    """
    Simple session object that generates questions once and returns them in order.
    Example:
        s = InterviewSession("Backend Engineer", n_questions=5)
        s.next_question()  # returns "Question 1: ..."
        s.next_question()  # returns "Question 2: ..."
        s.has_next()       # whether more remain
    """

    def __init__(self, job_title: str, n_questions: int = 10):
        self.job_title = job_title
        self.n_questions = max(1, int(n_questions))
        self._questions: List[str] = generate_questions(job_title, self.n_questions)
        self._index = 0

    def next_question(self) -> Optional[str]:
        """Return the next question (prefixed 'Question N: ...') or None if finished."""
        if self._index >= len(self._questions):
            return None
        q = self._questions[self._index]
        self._index += 1
        return f"Question {self._index}: {q}"

    def peek_current(self) -> Optional[str]:
        """Return current question (without advancing), or None if none loaded."""
        if self._index == 0:
            return None
        idx = self._index - 1
        return f"Question {idx+1}: {self._questions[idx]}"

    def has_next(self) -> bool:
        return self._index < len(self._questions)

    def reset(self):
        self._index = 0

    def all_questions(self) -> List[str]:
        return list(self._questions)


# ----------------- If run directly, small demo -----------------
if __name__ == "__main__":
    print("Interview engine demo (Gemini available?)", bool(MODEL))
    sess = InterviewSession("Software Engineer", n_questions=5)
    while True:
        q = sess.next_question()
        if not q:
            break
        print(q)
        # Demo feedback fallback
        print("FEEDBACK (demo):")
        print(get_feedback_on_answer(q, "I led a project and solved tasks."))
        print("----")
