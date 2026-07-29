import sqlite3
from datetime import datetime, timezone

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

SUMMARY_PROMPT = """Summarize this conversation history concisely, preserving \
any facts, numbers, or decisions that might matter for follow-up questions. \
Keep it under 100 words.

{existing_summary}

New turns to fold in:
{new_turns}

Updated summary:"""


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )


def _connect():
    conn = sqlite3.connect(settings.MEMORY_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS memory_summary (
            session_id TEXT PRIMARY KEY,
            summary TEXT NOT NULL,
            summarized_through INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def save_turn(session_id: str, question: str, answer: str):
    conn = _connect()
    cur = conn.execute(
        "SELECT COALESCE(MAX(turn), 0) AS max_turn FROM conversations WHERE session_id = ?",
        (session_id,),
    )
    next_turn = cur.fetchone()["max_turn"] + 1
    conn.execute(
        "INSERT INTO conversations (session_id, turn, question, answer, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, next_turn, question, answer, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return next_turn


def _get_summary_row(conn, session_id: str):
    row = conn.execute(
        "SELECT summary, summarized_through FROM memory_summary WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return (row["summary"], row["summarized_through"]) if row else ("", 0)


def _upsert_summary(conn, session_id: str, summary: str, summarized_through: int):
    conn.execute(
        """INSERT INTO memory_summary (session_id, summary, summarized_through)
           VALUES (?, ?, ?)
           ON CONFLICT(session_id) DO UPDATE SET summary = excluded.summary,
                                                  summarized_through = excluded.summarized_through""",
        (session_id, summary, summarized_through),
    )
    conn.commit()


def get_memory_context(session_id: str, max_raw: int = None) -> str:
    max_raw = max_raw if max_raw is not None else settings.MEMORY_MAX_RAW_TURNS
    conn = _connect()

    all_turns = conn.execute(
        "SELECT turn, question, answer FROM conversations WHERE session_id = ? ORDER BY turn ASC",
        (session_id,),
    ).fetchall()

    if not all_turns:
        conn.close()
        return ""

    older = all_turns[:-max_raw] if len(all_turns) > max_raw else []
    recent = all_turns[-max_raw:] if len(all_turns) > max_raw else all_turns

    existing_summary, summarized_through = _get_summary_row(conn, session_id)
    new_older = [t for t in older if t["turn"] > summarized_through]

    if new_older:
        new_turns_text = "\n".join(f"Q: {t['question']}\nA: {t['answer']}" for t in new_older)
        try:
            llm = get_llm()
            prompt = SUMMARY_PROMPT.format(
                existing_summary=existing_summary or "(no prior summary)",
                new_turns=new_turns_text,
            )
            response = llm.invoke(prompt)
            existing_summary = response.content.strip()
            summarized_through = new_older[-1]["turn"]
            _upsert_summary(conn, session_id, existing_summary, summarized_through)
        except Exception:
            pass

    conn.close()

    parts = []
    if existing_summary:
        parts.append(f"Summary of earlier conversation:\n{existing_summary}")
    if recent:
        recent_text = "\n".join(f"Q: {t['question']}\nA: {t['answer']}" for t in recent)
        parts.append(f"Recent turns:\n{recent_text}")

    return "\n\n".join(parts)


if __name__ == "__main__":
    init_db()
    session = "test-session"

    save_turn(session, "How many customers have churned in the last 90 days?", "27 customers have churned.")
    save_turn(session, "What plan are most of them on?", "Most churned customers were on the Basic plan.")

    context = get_memory_context(session)
    print("Memory context after 2 turns:\n")
    print(context)
