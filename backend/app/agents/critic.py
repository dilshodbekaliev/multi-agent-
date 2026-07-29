from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.state import AgentState, new_state
from app.tracing import get_langfuse_callbacks

CRITIC_PROMPT = """You are a strict fact-checker reviewing a draft answer \
before it's shown to a business user.

Question: {question}

--- Evidence available ---
Documents: {documents}
SQL result: {sql_result}
Code result: {code_result}

--- Draft answer to review ---
{answer}

Check:
1. Is every factual claim in the draft actually supported by the evidence above?
2. Does the draft fully address the question (not partially, not off-topic)?

Rules:
- If both checks pass, output exactly: PASS
- If either check fails, output: FAIL: <one specific, actionable sentence on what to fix>
- No other text.

Verdict:"""


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        callbacks=get_langfuse_callbacks(),
    )


def critic_node(state: AgentState) -> dict:
    llm = get_llm()

    documents_text = "\n\n".join(state.get("documents", [])) or "(none)"
    sql_text = state.get("sql_result") or "(none)"
    code_text = state.get("code_result") or "(none)"

    prompt = CRITIC_PROMPT.format(
        question=state["question"],
        documents=documents_text,
        sql_result=sql_text,
        code_result=code_text,
        answer=state.get("answer", ""),
    )

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
    except Exception as e:
        return {
            "critique_passed": True,
            "critique_feedback": None,
            "steps": [f"critic: error, passing through — {e}"],
        }

    passed = raw.upper().startswith("PASS")
    feedback = None if passed else raw

    return {
        "critique_passed": passed,
        "critique_feedback": feedback,
        "revisions": state.get("revisions", 0) + (0 if passed else 1),
        "steps": [f"critic: {'PASS' if passed else raw}"],
    }


if __name__ == "__main__":
    state = new_state("How many customers have churned in the last 90 days?")
    state["documents"] = []
    state["sql_result"] = "SQL: SELECT COUNT(*) ...\nColumns: ['COUNT(*)']\nRows: [(27,)]"
    state["answer"] = "Roughly 50 customers churned recently, mostly due to poor support."

    update = critic_node(state)
    print("Steps:")
    for s in update["steps"]:
        print(" -", s)
    print("\ncritique_passed:", update["critique_passed"])
    print("critique_feedback:", update["critique_feedback"])
