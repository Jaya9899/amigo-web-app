"""
amigo_focus_guard.py
====================
Amigo — Focus Guard Backend API
--------------------------------
Handles student focus-monitoring events sent from the frontend
when a student switches tabs, minimizes the window, or leaves
the classroom session.

Stack  : FastAPI + Uvicorn
Storage: In-memory (swap for Redis / Postgres in production)

Endpoints
---------
POST /api/focus/event          — frontend fires this on tab-switch / blur
GET  /api/focus/status/{sid}   — fetch a student's current focus stats
GET  /api/focus/messages        — get the pool of Gen-Z notification messages
POST /api/focus/reset/{sid}    — reset a student's distraction counter
GET  /api/health               — health check

Run
---
    pip install fastapi uvicorn pydantic
    python amigo_focus_guard.py
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import random


# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="Amigo Focus Guard API",
    description="Backend for student focus-monitoring and friendly re-engagement notifications 🐼",
    version="1.0.0",
)

# Allow the frontend (any origin during dev — lock this down in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# In-memory store  (replace with DB in prod)
# ─────────────────────────────────────────────

# { student_id: { "name": str, "distractions": int, "last_seen": datetime, "session_id": str } }
student_focus: dict[str, dict] = {}


# ─────────────────────────────────────────────
# Gen-Z notification messages
# ─────────────────────────────────────────────

MESSAGES = [
    {
        "id": 1,
        "headline": "bestie, u left me 😭",
        "body": "no cap, the lecture is lowkey fire rn and you're missing it 🔥 ur future self is begging you to come back fr fr",
        "cta": "ok ok i'm back 🐼",
        "severity": "gentle",
    },
    {
        "id": 2,
        "headline": "ayo come back!! 🐾",
        "body": "i literally paused everything waiting for you 🥺 the class ain't it without you, no cap — slay but study first bestie",
        "cta": "yasss coming back 💅",
        "severity": "gentle",
    },
    {
        "id": 3,
        "headline": "bro… really? 😤",
        "body": "that other tab can WAIT, this unit exam cannot 💀 ur the main character of this story — act like it 👑",
        "cta": "aight aight i'm focused 🙏",
        "severity": "medium",
    },
    {
        "id": 4,
        "headline": "i miss u already 🌿",
        "body": "ok real talk — 5 more minutes and you'll actually get this topic, i pinky promise it's worth it 🤙✨",
        "cta": "fine, let's lock in 🔒",
        "severity": "gentle",
    },
    {
        "id": 5,
        "headline": "hello?? earth to student 📡",
        "body": "the wifi in that other tab isn't gonna get you that A grade bestie 😭 come back, let's lock in together 💪",
        "cta": "ok ok locking in 🫡",
        "severity": "medium",
    },
    {
        "id": 6,
        "headline": "nuh uh, not on my watch 🐼",
        "body": "i see you tryna escape lol 👀 we're in a vibe check rn and class is the vibe — now come back slay ✨",
        "cta": "slaying AND studying 💯",
        "severity": "medium",
    },
    {
        "id": 7,
        "headline": "ok this is ur villain arc 😈",
        "body": "skipping class era? bestie no 💔 i believed in you and you chose that other tab smh… redemption arc starts NOW",
        "cta": "redemption arc activated 🦋",
        "severity": "firm",
    },
    {
        "id": 8,
        "headline": "sending u brainrot energy 🧠",
        "body": "fr fr though the exam is not gonna rizz itself 💀 u got the rizz, now apply it to these algorithms bestie",
        "cta": "rizzed up and ready 😤",
        "severity": "firm",
    },
    {
        "id": 9,
        "headline": "ur streak is crying rn 😢",
        "body": "every time you leave, a study streak loses its wings 🪽 come back before the vibe fully dies pls",
        "cta": "saving the streak 🏃",
        "severity": "medium",
    },
    {
        "id": 10,
        "headline": "it's giving… distracted 💨",
        "body": "and we are NOT doing the distracted era rn bestie 🚫 the focused era is so much more aesthetic trust",
        "cta": "focused era activated ✨",
        "severity": "gentle",
    },
]


# ─────────────────────────────────────────────
# Request / Response models
# ─────────────────────────────────────────────

class FocusEvent(BaseModel):
    student_id: str
    student_name: Optional[str] = "Student"
    session_id: str
    event_type: str          # "tab_hidden" | "window_blur" | "tab_visible" | "window_focus"
    timestamp: Optional[str] = None


class FocusEventResponse(BaseModel):
    student_id: str
    event_type: str
    distraction_count: int
    should_notify: bool
    message: Optional[dict] = None
    severity: str
    timestamp: str


class StudentStatus(BaseModel):
    student_id: str
    student_name: str
    session_id: str
    distraction_count: int
    last_seen: str
    focus_score: int         # 0–100
    status: str              # "focused" | "distracted" | "returned"


# ─────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────

def get_or_create_student(student_id: str, student_name: str, session_id: str) -> dict:
    """Return existing student record or create a fresh one."""
    if student_id not in student_focus:
        student_focus[student_id] = {
            "name": student_name,
            "session_id": session_id,
            "distractions": 0,
            "last_seen": datetime.now(timezone.utc).isoformat(),
            "status": "focused",
        }
    return student_focus[student_id]


def pick_message(distraction_count: int) -> dict:
    """
    Pick a notification message based on how many times
    the student has been distracted this session.
    Earlier distractions → gentle messages.
    Repeated distractions → progressively firmer.
    """
    if distraction_count <= 2:
        pool = [m for m in MESSAGES if m["severity"] == "gentle"]
    elif distraction_count <= 5:
        pool = [m for m in MESSAGES if m["severity"] in ("gentle", "medium")]
    else:
        pool = MESSAGES  # all messages including firm ones

    return random.choice(pool)


def compute_focus_score(distractions: int) -> int:
    """
    Simple focus score: starts at 100, drops 10 per distraction,
    floors at 0.
    """
    return max(0, 100 - (distractions * 10))


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/api/health")
def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "service": "Amigo Focus Guard 🐼",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/focus/event", response_model=FocusEventResponse)
def handle_focus_event(event: FocusEvent):
    """
    Called by the frontend whenever the student leaves or returns
    to the classroom tab/window.

    - On leave events  (tab_hidden / window_blur)  → increment distraction
      counter and return a notification message.
    - On return events (tab_visible / window_focus) → mark student as back,
      no notification needed.
    """
    now = datetime.now(timezone.utc).isoformat()

    student = get_or_create_student(
        event.student_id,
        event.student_name or "Student",
        event.session_id,
    )

    LEAVE_EVENTS  = {"tab_hidden", "window_blur"}
    RETURN_EVENTS = {"tab_visible", "window_focus"}

    if event.event_type in LEAVE_EVENTS:
        student["distractions"] += 1
        student["status"] = "distracted"
        student["last_seen"] = now

        message  = pick_message(student["distractions"])
        severity = message["severity"]

        return FocusEventResponse(
            student_id       = event.student_id,
            event_type       = event.event_type,
            distraction_count= student["distractions"],
            should_notify    = True,
            message          = message,
            severity         = severity,
            timestamp        = now,
        )

    elif event.event_type in RETURN_EVENTS:
        student["status"] = "focused"
        student["last_seen"] = now

        return FocusEventResponse(
            student_id        = event.student_id,
            event_type        = event.event_type,
            distraction_count = student["distractions"],
            should_notify     = False,
            message           = None,
            severity          = "none",
            timestamp         = now,
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown event_type '{event.event_type}'. "
                   f"Use: tab_hidden | window_blur | tab_visible | window_focus",
        )


@app.get("/api/focus/status/{student_id}", response_model=StudentStatus)
def get_student_status(student_id: str):
    """
    Fetch the current focus stats for a student.
    Useful for teacher dashboards to monitor engagement.
    """
    if student_id not in student_focus:
        raise HTTPException(
            status_code=404,
            detail=f"Student '{student_id}' not found in this session.",
        )

    s = student_focus[student_id]
    return StudentStatus(
        student_id       = student_id,
        student_name     = s["name"],
        session_id       = s["session_id"],
        distraction_count= s["distractions"],
        last_seen        = s["last_seen"],
        focus_score      = compute_focus_score(s["distractions"]),
        status           = s["status"],
    )


@app.get("/api/focus/messages")
def get_all_messages():
    """
    Returns the full pool of Gen-Z notification messages.
    Frontend can pre-load these to show notifications
    without an extra round-trip.
    """
    return {
        "count": len(MESSAGES),
        "messages": MESSAGES,
    }


@app.post("/api/focus/reset/{student_id}")
def reset_student(student_id: str):
    """
    Reset a student's distraction counter back to zero.
    Call this at the start of a new session or when the
    teacher manually clears the record.
    """
    if student_id not in student_focus:
        raise HTTPException(
            status_code=404,
            detail=f"Student '{student_id}' not found.",
        )

    student_focus[student_id]["distractions"] = 0
    student_focus[student_id]["status"] = "focused"

    return {
        "success": True,
        "message": f"Focus record reset for student '{student_id}' 🐼",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/focus/all")
def get_all_students():
    """
    Returns focus stats for every student tracked in the current
    session. Designed for the teacher's live dashboard.
    """
    result = []
    for sid, s in student_focus.items():
        result.append({
            "student_id":        sid,
            "student_name":      s["name"],
            "session_id":        s["session_id"],
            "distraction_count": s["distractions"],
            "focus_score":       compute_focus_score(s["distractions"]),
            "status":            s["status"],
            "last_seen":         s["last_seen"],
        })

    # Sort by most distracted first (useful for teacher to spot at-risk students)
    result.sort(key=lambda x: x["distraction_count"], reverse=True)
    return {"total_students": len(result), "students": result}


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🐼  Amigo Focus Guard API is live!")
    print("📡  Docs → http://localhost:8000/docs\n")
    uvicorn.run("amigo_focus_guard:app", host="0.0.0.0", port=8000, reload=True)