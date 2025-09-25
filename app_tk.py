# app_tk.py
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# import interview engine API (must exist)
# from interview_engine import InterviewSession, generate_questions, get_feedback_on_answer
# If your file is named differently, adjust the import.
try:
    from interview_engine import InterviewSession, generate_questions, get_feedback_on_answer
except Exception as e:
    # Provide safe fallback implementations so UI still works without API
    print("Warning: interview_engine import failed:", e)

    class InterviewSession:
        def __init__(self, job_title, n_questions=10):
            self._questions = generate_questions(job_title, n_questions) if 'generate_questions' in globals() else [
                "Why should we hire you?",
                "Tell me about yourself.",
                "What are your strengths?",
                "What are your weaknesses?",
                "Where do you see yourself in 5 years?"
            ]
            self._index = 0

        def next_question(self):
            if self._index >= len(self._questions):
                return None
            self._index += 1
            return f"Question {self._index}: {self._questions[self._index - 1]}"

        def all_questions(self):
            return list(self._questions)

        def has_next(self):
            return self._index < len(self._questions)

        def reset(self):
            self._index = 0

    def generate_questions(job_title, n_questions=10):
        return [
            "Why should we hire you?",
            "Tell me about yourself.",
            "What are your strengths?",
            "What are your weaknesses?",
            "Where do you see yourself in 5 years?",
            "Why do you want to work here?",
            "Tell me about a challenge you faced at work.",
            "How do you handle stress?",
            "What motivates you?",
            "Do you have any questions for us?"
        ][:n_questions]

    def get_feedback_on_answer(question, answer):
        if not answer.strip():
            return "1) No answer given. Please write your answer.\n2) Try to include a short example.\n3) Give one result/outcome."
        # Simple fallback that creates step-by-step suggestions
        return "\n".join([
            "1) Score: 70/100",
            "2) Strength: Clear structure in your response.",
            "3) Improve: Add a concrete example with numbers.",
            "4) Improve: Briefly state result or impact.",
            "5) Example: I led X, implemented Y, which improved Z by 20%."
        ])

# ---------- styling ----------
BG = "#0f1724"             # dark background
CARD = "#111827"           # card background
QUESTION_FG = "#FFFFFF"    # white for questions
ANSWER_FG = "#E6EEF3"      # light for answers
FEEDBACK_TITLE = "#FFFFFF" # feedback title - bright white
FEEDBACK_STEP = "#A7F3D0"  # nice pale green steps
ACCENT = "#3B82F6"         # blue for buttons

TITLE_FONT = ("Segoe UI", 18, "bold")
Q_FONT = ("Segoe UI", 12, "bold")
A_FONT = ("Consolas", 11)
F_FONT = ("Consolas", 11)

# ---------- QuestionBlock: per-question widgets ----------
class QuestionBlock(tk.Frame):
    def __init__(self, parent, q_index: int, q_text: str, *args, **kwargs):
        super().__init__(parent, bg=CARD, padx=10, pady=8, *args, **kwargs)
        self.q_index = q_index
        self.q_text = q_text

        # Question header
        self.q_label = tk.Label(self, text=f"Question {q_index}:", font=Q_FONT, fg=FEEDBACK_TITLE, bg=CARD)
        self.q_label.pack(anchor="w")
        self.q_text_label = tk.Label(self, text=q_text, font=("Segoe UI", 12, "bold"),
                                     fg=QUESTION_FG, bg=CARD, wraplength=820, justify="left")
        self.q_text_label.pack(anchor="w", pady=(2,8))

        # Answer box (bigger)
        self.answer_label = tk.Label(self, text=f"Answer {q_index}:", font=Q_FONT, fg=FEEDBACK_TITLE, bg=CARD)
        self.answer_label.pack(anchor="w")
        self.answer_box = tk.Text(self, height=6, bg="#041328", fg=ANSWER_FG, insertbackground=ANSWER_FG,
                                  font=A_FONT, wrap="word", relief="flat")
        self.answer_box.pack(fill="x", pady=(4,6))

        # Buttons row
        btn_frame = tk.Frame(self, bg=CARD)
        btn_frame.pack(fill="x", pady=(0,6))
        self.fb_btn = tk.Button(btn_frame, text="Get Feedback", command=self.on_get_feedback,
                                bg=ACCENT, fg="white", relief="flat", padx=8, pady=4)
        self.fb_btn.pack(side="left")
        self.clear_btn = tk.Button(btn_frame, text="Clear Answer", command=self.clear_answer,
                                   bg="#374151", fg="white", relief="flat", padx=8, pady=4)
        self.clear_btn.pack(side="left", padx=(8,0))

        # Feedback area (bigger, dark)
        self.fb_label = tk.Label(self, text="Feedback:", font=Q_FONT, fg=FEEDBACK_TITLE, bg=CARD)
        self.fb_label.pack(anchor="w")
        self.feedback_area = scrolledtext.ScrolledText(self, height=8, bg="#021221",
                                                       fg=FEEDBACK_STEP, font=F_FONT, wrap="word", relief="flat")
        self.feedback_area.pack(fill="both", pady=(4,2))
        self.feedback_area.config(state="disabled")

    def clear_answer(self):
        self.answer_box.delete("1.0", tk.END)
        self.feedback_area.config(state="normal")
        self.feedback_area.delete("1.0", tk.END)
        self.feedback_area.config(state="disabled")

    def on_get_feedback(self):
        answer = self.answer_box.get("1.0", tk.END).strip()
        if not answer:
            messagebox.showwarning("Empty answer", "Please write an answer first.")
            return

        # disable button while working
        self.fb_btn.config(state="disabled", text="Working...")
        def task():
            fb_text = get_feedback_on_answer(self.q_text, answer)
            # ensure step-by-step: split lines, but preserve structured replies from the model
            lines = []
            for ln in fb_text.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                lines.append(ln)
            # if returned as paragraph, split into short sentences
            if len(lines) == 1 and len(lines[0].split(".")) > 1:
                pieces = [p.strip() for p in lines[0].split(".") if p.strip()]
                lines = [p for p in pieces]

            # update UI on main thread
            self.after(0, self._show_feedback, answer, lines)

        threading.Thread(target=task, daemon=True).start()

    def _show_feedback(self, answer, lines):
        # show user's answer first (title + answer)
        self.feedback_area.config(state="normal")
        self.feedback_area.delete("1.0", tk.END)
        self.feedback_area.insert(tk.END, "Your Answer:\n", ("fb_title",))
        self.feedback_area.insert(tk.END, answer.strip() + "\n\n", ("fb_answer",))
        # then add step-by-step feedback numbered
        self.feedback_area.insert(tk.END, "Feedback (step-by-step):\n", ("fb_title",))
        for i, ln in enumerate(lines, start=1):
            # friendly formatting: "1) ..." and color
            self.feedback_area.insert(tk.END, f"{i}) {ln}\n", ("fb_step",))
        self.feedback_area.config(state="disabled")
        # restore button text
        self.fb_btn.config(state="normal", text="Get Feedback")
        # ensure the block is visible (scroll parent canvas)
        try:
            self.master.update_idletasks()
            # scroll canvas to this block's position if inside a canvas
            p = self.winfo_rooty() - self.master.winfo_rooty()
            self.master.yview_moveto(max(0, p / max(1, self.master.winfo_height())))
        except Exception:
            pass

# ---------- Main application ----------
class InterviewApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI-Interview_Assistant")
        self.geometry("980x760")
        self.configure(bg=BG)

        # Header
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=12, pady=12)
        tk.Label(header, text="AI-Interview_Assistant", font=TITLE_FONT, fg="#FDE68A", bg=BG).pack()

        # Job input + buttons
        ctl = tk.Frame(self, bg=BG)
        ctl.pack(fill="x", padx=12, pady=(4,8))
        tk.Label(ctl, text="Job Title:", fg="white", bg=BG, font=("Segoe UI", 11)).pack(side="left")
        self.job_entry = tk.Entry(ctl, font=("Segoe UI", 12), width=40, bg="#041328", fg="white", insertbackground="white")
        self.job_entry.pack(side="left", padx=(8,12))
        self.job_entry.insert(0, "Data Scientist")

        # Buttons
        btn_next = tk.Button(ctl, text="Next Question", command=self.on_next_question, bg=ACCENT, fg="white", relief="flat")
        btn_next.pack(side="left", padx=(0,6))
        btn_all = tk.Button(ctl, text="Get All Questions", command=self.on_get_all_questions, bg="#10B981", fg="white", relief="flat")
        btn_all.pack(side="left", padx=(0,6))
        btn_clear = tk.Button(ctl, text="Clear", command=self.clear_all, bg="#EF4444", fg="white", relief="flat")
        btn_clear.pack(side="left")

        # status
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self.status_var, fg="#94A3B8", bg=BG).pack(anchor="w", padx=12)

        # scrollable area for QuestionBlocks
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True, padx=12, pady=10)

        self.canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=BG)

        self.scroll_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0,0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # style tags for feedback_area (applies to each ScrolledText inside blocks)
        # (we will configure tags on each feedback_area)
        self.q_blocks = []
        self.session = None

    # ---------- actions ----------
    def ensure_session(self):
        if not self.session:
            job = self.job_entry.get().strip()
            if not job:
                messagebox.showwarning("Missing job title", "Please enter a job title.")
                return False
            self.session = InterviewSession(job, n_questions=10)
            self.status_var.set(f"Session for '{job}' created")
        return True

    def on_next_question(self):
        if not self.ensure_session():
            return
        q = self.session.next_question()
        if not q:
            messagebox.showinfo("Finished", "No more questions in session.")
            return
        # q is like "Question N: text"
        # extract number and text
        if ":" in q:
            parts = q.split(":", 1)
            label = parts[0].strip()
            qtext = parts[1].strip()
            idx = int(label.replace("Question", "").strip())
        else:
            idx = len(self.q_blocks) + 1
            qtext = q
        block = QuestionBlock(self.scroll_frame, idx, qtext)
        # configure tags for feedback_area text colors
        block.feedback_area.tag_config("fb_title", foreground=FEEDBACK_TITLE, font=("Segoe UI", 11, "bold"))
        block.feedback_area.tag_config("fb_answer", foreground=ANSWER_FG, font=("Consolas", 11))
        block.feedback_area.tag_config("fb_step", foreground=FEEDBACK_STEP, font=("Consolas", 11))
        block.pack(fill="x", pady=8, padx=6)
        self.q_blocks.append(block)
        self._scroll_to_bottom()

    def on_get_all_questions(self):
        job = self.job_entry.get().strip()
        if not job:
            messagebox.showwarning("Missing job title", "Please enter a job title.")
            return
        self.status_var.set("Generating questions...")
        # fetch in background
        def task():
            qs = generate_questions(job, n_questions=10)
            self.after(0, self._populate_all_questions, qs)
        threading.Thread(target=task, daemon=True).start()

    def _populate_all_questions(self, questions):
        self.clear_all()
        for i, q in enumerate(questions, start=1):
            block = QuestionBlock(self.scroll_frame, i, q)
            block.feedback_area.tag_config("fb_title", foreground=FEEDBACK_TITLE, font=("Segoe UI", 11, "bold"))
            block.feedback_area.tag_config("fb_answer", foreground=ANSWER_FG, font=("Consolas", 11))
            block.feedback_area.tag_config("fb_step", foreground=FEEDBACK_STEP, font=("Consolas", 11))
            block.pack(fill="x", pady=8, padx=6)
            self.q_blocks.append(block)
        self.status_var.set(f"{len(questions)} questions loaded")
        self._scroll_to_bottom()

    def feedback_for_block(self, block: QuestionBlock):
        # convenience if needed: call block.on_get_feedback()
        block.on_get_feedback()

    def clear_all(self):
        for b in self.q_blocks:
            b.destroy()
        self.q_blocks = []
        self.session = None
        self.status_var.set("Cleared")
        self.canvas.yview_moveto(0)

    def _scroll_to_bottom(self):
        self.update_idletasks()
        # move view to bottom
        self.canvas.yview_moveto(1.0)

# ---------- run ----------
if __name__ == "__main__":
    root = InterviewApp()
    root.mainloop()
