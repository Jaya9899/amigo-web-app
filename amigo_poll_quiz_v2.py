"""
amigo_poll_quiz_v2.py
=====================
Amigo — Poll & Quiz Backend API  (v2 — Role-Separated + Persistent SQLite DB)
------------------------------------------------------------------------------
Run:
    pip install fastapi uvicorn pydantic
    python amigo_poll_quiz_v2.py
"""

import uvicorn
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Amigo Poll & Quiz API v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "amigo_classroom.db"


# ── Database ──────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

@contextmanager
def db():
    conn = get_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id   TEXT PRIMARY KEY,
            faculty_id   TEXT NOT NULL,
            course_code  TEXT,
            topic        TEXT,
            created_at   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS polls (
            poll_id      TEXT PRIMARY KEY,
            session_id   TEXT NOT NULL,
            faculty_id   TEXT NOT NULL,
            question     TEXT NOT NULL,
            topic        TEXT,
            duration_sec INTEGER DEFAULT 30,
            status       TEXT DEFAULT 'active',
            created_at   TEXT NOT NULL,
            closed_at    TEXT
        );
        CREATE TABLE IF NOT EXISTS poll_options (
            option_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id      TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            option_text  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS poll_responses (
            response_id         TEXT PRIMARY KEY,
            poll_id             TEXT NOT NULL,
            student_id          TEXT NOT NULL,
            student_name        TEXT,
            chosen_option_index INTEGER NOT NULL,
            chosen_option_text  TEXT NOT NULL,
            submitted_at        TEXT NOT NULL,
            UNIQUE(poll_id, student_id)
        );
        CREATE TABLE IF NOT EXISTS quizzes (
            quiz_id              TEXT PRIMARY KEY,
            session_id           TEXT NOT NULL,
            faculty_id           TEXT NOT NULL,
            question             TEXT NOT NULL,
            topic                TEXT,
            correct_option_index INTEGER NOT NULL,
            allow_text_answer    INTEGER DEFAULT 0,
            max_marks            REAL DEFAULT 1.0,
            duration_sec         INTEGER DEFAULT 20,
            status               TEXT DEFAULT 'active',
            answer_revealed      INTEGER DEFAULT 0,
            created_at           TEXT NOT NULL,
            closed_at            TEXT
        );
        CREATE TABLE IF NOT EXISTS quiz_options (
            option_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id      TEXT NOT NULL,
            option_index INTEGER NOT NULL,
            option_text  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quiz_responses (
            response_id         TEXT PRIMARY KEY,
            quiz_id             TEXT NOT NULL,
            student_id          TEXT NOT NULL,
            student_name        TEXT,
            chosen_option_index INTEGER,
            text_answer         TEXT,
            is_correct          INTEGER,
            marks_awarded       REAL,
            submitted_at        TEXT NOT NULL,
            UNIQUE(quiz_id, student_id)
        );
        """)
    print("Database ready ->", DB_PATH)


# ── Helpers ───────────────────────────────────────────────────────

def now():
    return datetime.now(timezone.utc).isoformat()

def short_id():
    return str(uuid.uuid4())[:8]

def require_faculty(role):
    if role.lower() != "faculty":
        raise HTTPException(status_code=403, detail="Only faculty can perform this action.")

def require_student(role):
    if role.lower() != "student":
        raise HTTPException(status_code=403, detail="Only students can perform this action.")

def fetch_poll_options(conn, poll_id):
    rows = conn.execute(
        "SELECT option_index, option_text FROM poll_options WHERE poll_id=? ORDER BY option_index",
        (poll_id,)
    ).fetchall()
    return [{"index": r["option_index"], "text": r["option_text"]} for r in rows]

def fetch_quiz_options(conn, quiz_id):
    rows = conn.execute(
        "SELECT option_index, option_text FROM quiz_options WHERE quiz_id=? ORDER BY option_index",
        (quiz_id,)
    ).fetchall()
    return [{"index": r["option_index"], "text": r["option_text"]} for r in rows]


# ── Models ────────────────────────────────────────────────────────

class CreateSession(BaseModel):
    faculty_id:  str
    course_code: Optional[str] = None
    topic:       Optional[str] = None

class CreatePoll(BaseModel):
    faculty_id:       str
    session_id:       str
    question:         str
    options:          list[str]
    topic:            Optional[str] = None
    duration_seconds: int = 30

class CreateQuiz(BaseModel):
    faculty_id:           str
    session_id:           str
    question:             str
    options:              list[str]
    correct_option_index: int
    topic:                Optional[str] = None
    max_marks:            float = 1.0
    allow_text_answer:    bool  = False
    duration_seconds:     int   = 20

class PollRespond(BaseModel):
    student_id:          str
    student_name:        Optional[str] = "Student"
    chosen_option_index: int

class QuizRespond(BaseModel):
    student_id:          str
    student_name:        Optional[str] = "Student"
    chosen_option_index: Optional[int] = None
    text_answer:         Optional[str] = None


# ── Health ────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Amigo Poll & Quiz API v2", "timestamp": now()}


# ── FACULTY — Session ─────────────────────────────────────────────

@app.post("/faculty/session/create")
def create_session(data: CreateSession, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    session_id = short_id()
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?)",
            (session_id, data.faculty_id, data.course_code, data.topic, now())
        )
    return {"success": True, "session_id": session_id, "message": "Session created!"}


# ── FACULTY — Create poll ─────────────────────────────────────────

@app.post("/faculty/poll/create")
def create_poll(data: CreatePoll, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    if not (2 <= len(data.options) <= 6):
        raise HTTPException(status_code=400, detail="Need 2 to 6 options.")
    poll_id = short_id()
    with db() as conn:
        conn.execute(
            "INSERT INTO polls VALUES (?,?,?,?,?,?,?,?,?)",
            (poll_id, data.session_id, data.faculty_id,
             data.question, data.topic, data.duration_seconds, "active", now(), None)
        )
        for i, opt in enumerate(data.options):
            conn.execute(
                "INSERT INTO poll_options (poll_id, option_index, option_text) VALUES (?,?,?)",
                (poll_id, i, opt)
            )
    return {"success": True, "poll_id": poll_id, "question": data.question,
            "options": data.options, "message": "Poll is now live for students!"}


# ── FACULTY — Create quiz ─────────────────────────────────────────

@app.post("/faculty/quiz/create")
def create_quiz(data: CreateQuiz, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    if not (2 <= len(data.options) <= 6):
        raise HTTPException(status_code=400, detail="Need 2 to 6 options.")
    if not (0 <= data.correct_option_index < len(data.options)):
        raise HTTPException(status_code=400, detail="correct_option_index out of range.")
    quiz_id = short_id()
    with db() as conn:
        conn.execute(
            "INSERT INTO quizzes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (quiz_id, data.session_id, data.faculty_id,
             data.question, data.topic, data.correct_option_index,
             int(data.allow_text_answer), data.max_marks,
             data.duration_seconds, "active", 0, now(), None)
        )
        for i, opt in enumerate(data.options):
            conn.execute(
                "INSERT INTO quiz_options (quiz_id, option_index, option_text) VALUES (?,?,?)",
                (quiz_id, i, opt)
            )
    return {"success": True, "quiz_id": quiz_id, "question": data.question,
            "options": data.options, "message": "Quiz is now live for students!"}


# ── FACULTY — Close poll ──────────────────────────────────────────

@app.post("/faculty/poll/{poll_id}/close")
def close_poll(poll_id: str, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    with db() as conn:
        poll = conn.execute("SELECT * FROM polls WHERE poll_id=?", (poll_id,)).fetchone()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found.")
        if poll["status"] == "closed":
            return {"message": "Already closed.", "poll_id": poll_id}
        conn.execute("UPDATE polls SET status='closed', closed_at=? WHERE poll_id=?", (now(), poll_id))
        responses = conn.execute("SELECT * FROM poll_responses WHERE poll_id=?", (poll_id,)).fetchall()
        options   = fetch_poll_options(conn, poll_id)
    tally = [0] * len(options)
    for r in responses:
        tally[r["chosen_option_index"]] += 1
    total = len(responses)
    breakdown = sorted(
        [{"option": options[i]["text"], "votes": tally[i],
          "percentage": round(tally[i]/total*100, 1) if total else 0.0}
         for i in range(len(options))],
        key=lambda x: x["votes"], reverse=True
    )
    return {"success": True, "poll_id": poll_id, "total_votes": total, "breakdown": breakdown}


# ── FACULTY — Reveal quiz answer ──────────────────────────────────

@app.post("/faculty/quiz/{quiz_id}/reveal")
def reveal_quiz(quiz_id: str, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    with db() as conn:
        quiz = conn.execute("SELECT * FROM quizzes WHERE quiz_id=?", (quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        conn.execute(
            "UPDATE quizzes SET status='revealed', answer_revealed=1, closed_at=? WHERE quiz_id=?",
            (now(), quiz_id)
        )
        options = fetch_quiz_options(conn, quiz_id)
    return {"success": True, "quiz_id": quiz_id,
            "correct_option_index": quiz["correct_option_index"],
            "correct_answer": options[quiz["correct_option_index"]]["text"],
            "message": "Answer revealed to students!"}


# ── FACULTY — Poll results ────────────────────────────────────────

@app.get("/faculty/poll/{poll_id}/results")
def poll_results(poll_id: str, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    with db() as conn:
        poll = conn.execute("SELECT * FROM polls WHERE poll_id=?", (poll_id,)).fetchone()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found.")
        responses = conn.execute("SELECT * FROM poll_responses WHERE poll_id=?", (poll_id,)).fetchall()
        options   = fetch_poll_options(conn, poll_id)
    tally = [0] * len(options)
    for r in responses:
        tally[r["chosen_option_index"]] += 1
    total = len(responses)
    breakdown = sorted(
        [{"index": i, "option": options[i]["text"], "votes": tally[i],
          "percentage": round(tally[i]/total*100, 1) if total else 0.0}
         for i in range(len(options))],
        key=lambda x: x["votes"], reverse=True
    )
    return {"poll_id": poll_id, "question": poll["question"], "topic": poll["topic"],
            "status": poll["status"], "total_votes": total, "breakdown": breakdown,
            "leading": breakdown[0]["option"] if total else None}


# ── FACULTY — Quiz results ────────────────────────────────────────

@app.get("/faculty/quiz/{quiz_id}/results")
def quiz_results(quiz_id: str, x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    with db() as conn:
        quiz = conn.execute("SELECT * FROM quizzes WHERE quiz_id=?", (quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        responses = conn.execute("SELECT * FROM quiz_responses WHERE quiz_id=?", (quiz_id,)).fetchall()
        options   = fetch_quiz_options(conn, quiz_id)
    total    = len(responses)
    correct  = sum(1 for r in responses if r["is_correct"] == 1)
    avg_marks = (
        round(sum(r["marks_awarded"] for r in responses if r["marks_awarded"] is not None)/total, 2)
        if total else 0.0
    )
    tally = [0] * len(options)
    for r in responses:
        if r["chosen_option_index"] is not None:
            tally[r["chosen_option_index"]] += 1
    breakdown = [
        {"index": i, "option": options[i]["text"], "votes": tally[i],
         "percentage": round(tally[i]/total*100, 1) if total else 0.0,
         "is_correct": i == quiz["correct_option_index"]}
        for i in range(len(options))
    ]
    return {"quiz_id": quiz_id, "question": quiz["question"], "topic": quiz["topic"],
            "status": quiz["status"], "answer_revealed": bool(quiz["answer_revealed"]),
            "correct_answer": options[quiz["correct_option_index"]]["text"],
            "total_responses": total, "correct_count": correct, "wrong_count": total - correct,
            "accuracy_percent": round(correct/total*100, 1) if total else 0.0,
            "avg_marks": avg_marks, "max_marks": quiz["max_marks"], "breakdown": breakdown,
            "text_answers": [{"student_id": r["student_id"], "student_name": r["student_name"],
                              "answer": r["text_answer"]} for r in responses if r["text_answer"]]}


# ── FACULTY — Session summary / analytics ─────────────────────────

@app.get("/faculty/session/{session_id}/summary")
def session_summary(session_id: str, total_enrolled: int = 1,
                    x_role: str = Header(default="faculty")):
    require_faculty(x_role)
    with db() as conn:
        session = conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        all_polls   = conn.execute("SELECT * FROM polls WHERE session_id=?",   (session_id,)).fetchall()
        all_quizzes = conn.execute("SELECT * FROM quizzes WHERE session_id=?", (session_id,)).fetchall()

    poll_summaries = []
    for poll in all_polls:
        with db() as conn:
            responses = conn.execute("SELECT * FROM poll_responses WHERE poll_id=?", (poll["poll_id"],)).fetchall()
            options   = fetch_poll_options(conn, poll["poll_id"])
        tally = [0] * len(options)
        for r in responses:
            tally[r["chosen_option_index"]] += 1
        poll_summaries.append({
            "poll_id": poll["poll_id"], "question": poll["question"], "topic": poll["topic"],
            "total_votes": len(responses),
            "response_rate_percent": round(len(responses)/total_enrolled*100, 1),
            "most_chosen": options[tally.index(max(tally))]["text"] if responses else None
        })

    quiz_summaries  = []
    topic_stats     = {}
    student_scores  = {}
    most_missed     = []

    for quiz in all_quizzes:
        with db() as conn:
            responses = conn.execute("SELECT * FROM quiz_responses WHERE quiz_id=?", (quiz["quiz_id"],)).fetchall()
            options   = fetch_quiz_options(conn, quiz["quiz_id"])
        total_r   = len(responses)
        correct   = sum(1 for r in responses if r["is_correct"] == 1)
        accuracy  = round(correct/total_r*100, 1) if total_r else 0.0
        avg_marks = (
            round(sum(r["marks_awarded"] for r in responses if r["marks_awarded"] is not None)/total_r, 2)
            if total_r else 0.0
        )
        quiz_summaries.append({
            "quiz_id": quiz["quiz_id"], "question": quiz["question"], "topic": quiz["topic"],
            "total_responses": total_r,
            "response_rate_percent": round(total_r/total_enrolled*100, 1),
            "correct_count": correct, "wrong_count": total_r - correct,
            "accuracy_percent": accuracy, "avg_marks": avg_marks, "max_marks": quiz["max_marks"],
        })
        if total_r > 0 and accuracy < 50.0:
            most_missed.append({
                "quiz_id": quiz["quiz_id"], "question": quiz["question"], "topic": quiz["topic"],
                "accuracy_percent": accuracy,
                "correct_answer": options[quiz["correct_option_index"]]["text"]
            })
        topic = quiz["topic"] or "General"
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0, "marks_sum": 0.0, "marks_count": 0}
        topic_stats[topic]["correct"] += correct
        topic_stats[topic]["total"]   += total_r
        if total_r:
            topic_stats[topic]["marks_sum"]   += avg_marks * total_r
            topic_stats[topic]["marks_count"] += total_r
        for r in responses:
            sid = r["student_id"]
            if sid not in student_scores:
                student_scores[sid] = {"student_name": r["student_name"], "correct": 0, "total": 0, "marks": 0.0}
            student_scores[sid]["total"] += 1
            if r["is_correct"] == 1:
                student_scores[sid]["correct"] += 1
            if r["marks_awarded"]:
                student_scores[sid]["marks"] += r["marks_awarded"]

    topic_comprehension = []
    struggling_topics   = []
    for topic, stats in topic_stats.items():
        comp  = round(stats["correct"]/stats["total"]*100, 1) if stats["total"] else 0.0
        avg_m = round(stats["marks_sum"]/stats["marks_count"], 2) if stats["marks_count"] else 0.0
        entry = {"topic": topic, "total_responses": stats["total"],
                 "comprehension_percent": comp, "avg_marks": avg_m,
                 "status": "Good" if comp >= 75 else ("Needs work" if comp >= 50 else "Struggling")}
        topic_comprehension.append(entry)
        if comp < 60.0:
            struggling_topics.append({"topic": topic, "comprehension_percent": comp})

    student_breakdown = sorted(
        [{"student_id": sid, "student_name": s["student_name"],
          "questions_seen": s["total"], "correct": s["correct"],
          "accuracy_percent": round(s["correct"]/s["total"]*100, 1) if s["total"] else 0.0,
          "total_marks": round(s["marks"], 2)}
         for sid, s in student_scores.items()],
        key=lambda x: x["total_marks"], reverse=True
    )

    all_resp_count   = sum(q["total_responses"] for q in quiz_summaries)
    overall_accuracy = (
        round(sum(q["correct_count"] for q in quiz_summaries)/all_resp_count*100, 1)
        if all_resp_count else 0.0
    )

    return {
        "session_id": session_id, "course_code": session["course_code"],
        "topic": session["topic"], "total_enrolled": total_enrolled, "generated_at": now(),
        "engagement": {
            "total_polls": len(all_polls), "total_quizzes": len(all_quizzes),
            "total_poll_responses": sum(p["total_votes"] for p in poll_summaries),
            "total_quiz_responses": all_resp_count,
            "avg_response_rate_percent": round(
                all_resp_count/(len(all_quizzes)*total_enrolled)*100, 1
            ) if all_quizzes and total_enrolled else 0.0,
        },
        "performance": {
            "overall_accuracy_percent": overall_accuracy,
            "avg_marks_across_session": round(
                sum(q["avg_marks"] for q in quiz_summaries)/len(quiz_summaries), 2
            ) if quiz_summaries else 0.0,
        },
        "topic_comprehension":   sorted(topic_comprehension, key=lambda x: x["comprehension_percent"]),
        "struggling_topics":     struggling_topics,
        "most_missed_questions": sorted(most_missed, key=lambda x: x["accuracy_percent"]),
        "quiz_summaries":        quiz_summaries,
        "poll_summaries":        poll_summaries,
        "student_breakdown":     student_breakdown,
    }


# ── STUDENT — Fetch active poll or quiz ───────────────────────────

@app.get("/student/active/{session_id}")
def get_active(session_id: str, x_role: str = Header(default="student")):
    require_student(x_role)
    with db() as conn:
        poll = conn.execute(
            "SELECT * FROM polls WHERE session_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        quiz = conn.execute(
            "SELECT * FROM quizzes WHERE session_id=? AND status='active' ORDER BY created_at DESC LIMIT 1",
            (session_id,)
        ).fetchone()
        active_items = []
        if poll:
            options = fetch_poll_options(conn, poll["poll_id"])
            active_items.append({
                "type": "poll", "id": poll["poll_id"], "question": poll["question"],
                "options": [o["text"] for o in options],
                "duration_seconds": poll["duration_sec"], "created_at": poll["created_at"],
            })
        if quiz:
            options = fetch_quiz_options(conn, quiz["quiz_id"])
            item = {"type": "quiz", "id": quiz["quiz_id"], "question": quiz["question"],
                    "options": [o["text"] for o in options],
                    "allow_text_answer": bool(quiz["allow_text_answer"]),
                    "duration_seconds": quiz["duration_sec"], "created_at": quiz["created_at"]}
            if quiz["answer_revealed"]:
                item["correct_option_index"] = quiz["correct_option_index"]
            active_items.append(item)
    return {"session_id": session_id, "active_count": len(active_items), "items": active_items}


# ── STUDENT — Submit poll response ───────────────────────────────

@app.post("/student/poll/{poll_id}/respond")
def student_poll_respond(poll_id: str, data: PollRespond, x_role: str = Header(default="student")):
    require_student(x_role)
    with db() as conn:
        poll = conn.execute("SELECT * FROM polls WHERE poll_id=?", (poll_id,)).fetchone()
        if not poll:
            raise HTTPException(status_code=404, detail="Poll not found.")
        if poll["status"] == "closed":
            raise HTTPException(status_code=400, detail="This poll is already closed!")
        options = fetch_poll_options(conn, poll_id)
        if not (0 <= data.chosen_option_index < len(options)):
            raise HTTPException(status_code=400, detail=f"Choose option 0 to {len(options)-1}.")
        existing = conn.execute(
            "SELECT 1 FROM poll_responses WHERE poll_id=? AND student_id=?",
            (poll_id, data.student_id)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="You already voted in this poll!")
        conn.execute(
            "INSERT INTO poll_responses VALUES (?,?,?,?,?,?,?)",
            (short_id(), poll_id, data.student_id, data.student_name,
             data.chosen_option_index, options[data.chosen_option_index]["text"], now())
        )
        total = conn.execute(
            "SELECT COUNT(*) as c FROM poll_responses WHERE poll_id=?", (poll_id,)
        ).fetchone()["c"]
    return {"success": True, "poll_id": poll_id,
            "your_vote": options[data.chosen_option_index]["text"],
            "total_votes": total, "message": "Vote submitted!"}


# ── STUDENT — Submit quiz response ───────────────────────────────

@app.post("/student/quiz/{quiz_id}/respond")
def student_quiz_respond(quiz_id: str, data: QuizRespond, x_role: str = Header(default="student")):
    require_student(x_role)
    if data.chosen_option_index is None and not data.text_answer:
        raise HTTPException(status_code=400, detail="Provide a chosen_option_index or text_answer.")
    with db() as conn:
        quiz = conn.execute("SELECT * FROM quizzes WHERE quiz_id=?", (quiz_id,)).fetchone()
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        if quiz["status"] == "revealed":
            raise HTTPException(status_code=400, detail="This quiz has already ended!")
        options = fetch_quiz_options(conn, quiz_id)
        if data.chosen_option_index is not None:
            if not (0 <= data.chosen_option_index < len(options)):
                raise HTTPException(status_code=400, detail=f"Choose option 0 to {len(options)-1}.")
        existing = conn.execute(
            "SELECT 1 FROM quiz_responses WHERE quiz_id=? AND student_id=?",
            (quiz_id, data.student_id)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="You already answered this quiz!")
        is_correct = marks_awarded = None
        if data.chosen_option_index is not None:
            is_correct    = int(data.chosen_option_index == quiz["correct_option_index"])
            marks_awarded = float(quiz["max_marks"]) if is_correct else 0.0
        conn.execute(
            "INSERT INTO quiz_responses VALUES (?,?,?,?,?,?,?,?,?)",
            (short_id(), quiz_id, data.student_id, data.student_name,
             data.chosen_option_index, data.text_answer, is_correct, marks_awarded, now())
        )
        total = conn.execute(
            "SELECT COUNT(*) as c FROM quiz_responses WHERE quiz_id=?", (quiz_id,)
        ).fetchone()["c"]
    response = {"success": True, "quiz_id": quiz_id,
                "total_responses": total, "message": "Answer submitted!"}
    if data.chosen_option_index is not None:
        response["your_answer"] = options[data.chosen_option_index]["text"]
    if data.text_answer:
        response["your_text_answer"] = data.text_answer
    if quiz["answer_revealed"] and is_correct is not None:
        response["is_correct"]     = bool(is_correct)
        response["marks_awarded"]  = marks_awarded
        response["correct_answer"] = options[quiz["correct_option_index"]]["text"]
        response["feedback"]       = "Correct! You nailed it!" if is_correct else "Not quite — check the correct answer!"
    return response


# ── STUDENT — Own history ─────────────────────────────────────────

@app.get("/student/{student_id}/history")
def student_history(student_id: str, x_role: str = Header(default="student")):
    require_student(x_role)
    with db() as conn:
        poll_rows = conn.execute(
            "SELECT pr.*, p.question, p.topic FROM poll_responses pr "
            "JOIN polls p ON pr.poll_id=p.poll_id WHERE pr.student_id=? ORDER BY pr.submitted_at DESC",
            (student_id,)
        ).fetchall()
        quiz_rows = conn.execute(
            "SELECT qr.*, q.question, q.topic, q.correct_option_index, q.answer_revealed, q.max_marks "
            "FROM quiz_responses qr JOIN quizzes q ON qr.quiz_id=q.quiz_id "
            "WHERE qr.student_id=? ORDER BY qr.submitted_at DESC",
            (student_id,)
        ).fetchall()
    total_marks = total_possible = 0.0
    quizzes_out = []
    for r in quiz_rows:
        entry = {"quiz_id": r["quiz_id"], "question": r["question"],
                 "topic": r["topic"], "submitted_at": r["submitted_at"]}
        if r["answer_revealed"]:
            entry["is_correct"]    = bool(r["is_correct"])
            entry["marks_awarded"] = r["marks_awarded"]
            entry["max_marks"]     = r["max_marks"]
        if r["marks_awarded"] is not None:
            total_marks    += r["marks_awarded"]
            total_possible += r["max_marks"]
        quizzes_out.append(entry)
    return {
        "student_id": student_id,
        "poll_responses": [
            {"poll_id": r["poll_id"], "question": r["question"], "topic": r["topic"],
             "your_vote": r["chosen_option_text"], "submitted_at": r["submitted_at"]}
            for r in poll_rows
        ],
        "quiz_responses":  quizzes_out,
        "total_marks":     round(total_marks, 2),
        "total_possible":  round(total_possible, 2),
        "overall_percent": round(total_marks/total_possible*100, 1) if total_possible else 0.0,
    }


# ── Startup ───────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    init_db()


if __name__ == "__main__":
    print("\n📊  Amigo Poll & Quiz API v2 is live!")
    print("🧠  Docs  -> http://localhost:8001/docs")
    print("🗄️   DB    -> amigo_classroom.db\n")
    uvicorn.run("amigo_poll_quiz_v2:app", host="0.0.0.0", port=8001, reload=True)
