from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.state import AgentState, new_state
from app.tracing import get_langfuse_callbacks

VALID_AGENTS = {"retriever", "web", "sql", "code"}

ROUTE_PROMPT = """You are a routing supervisor for a team of specialist agents. \
Given the conversation so far and the current question, decide which agent(s) \
are needed to answer it.

Agents available:
- retriever: searches internal company documents/policies (e.g. churn definitions, playbooks, handbooks)
- web: searches the live internet (e.g. current events, exchange rates, prices, news)
- sql: queries a company database of customers/orders/products (e.g. counts, aggregates, churn numbers)
- code: runs Python for calculations/statistics on numbers already given in the question

{memory_block}
Rules:
- Output ONLY a comma-separated list of the agent names needed (from: retriever, web, sql, code).
- Use more than one if the question genuinely needs multiple sources.
- If the question is a follow-up (e.g. "what about last quarter instead"), use the conversation
  above to understand what it's really asking, then route based on that.
- No explanation, no other text.

Current question: {question}

Agents needed:"""

SYNTHESIS_PROMPT = """You are an analyst drafting a final answer for a business \
user. Use ONLY the evidence below — do not invent facts not present in it. \
If the evidence is insufficient, say so plainly.

{memory_block}
Current question: {question}

--- Evidence from internal documents ---
{documents}

--- Evidence from SQL database query ---
{sql_result}

--- Evidence from code execution ---
{code_result}
{revision_note}
Write a clear, concise answer (a few sentences, or a short list if that fits better). \
If this is a follow-up question, make sure your answer accounts for the earlier conversation.
Answer:"""

REVISION_NOTE_TEMPLATE = """
--- Your previous draft was rejected by the reviewer ---
Previous draft: {previous_answer}
Reviewer feedback: {feedback}
Produce an improved answer that fixes this specific issue.
"""


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        callbacks=get_langfuse_callbacks(),
    )


def _memory_block(state: AgentState) -> str:
    memory_context = state.get("memory_context", "")
    if not memory_context:
        return ""
    return f"--- Conversation so far ---\n{memory_context}\n"


def route(state: AgentState) -> dict:
    question = state["question"]
    llm = get_llm()

    try:
        response = llm.invoke(ROUTE_PROMPT.format(
            question=question,
            memory_block=_memory_block(state),
        ))
        raw = response.content.strip().lower()
        agents = [a.strip() for a in raw.split(",") if a.strip() in VALID_AGENTS]
    except Exception as e:
        agents = []
        raw = f"error: {e}"

    if not agents:
        agents = ["retriever"]

    return {
        "plan": ",".join(agents),
        "steps": [f"supervisor: routing to [{raw}] -> {agents}"],
    }


def route_to_agents(state: AgentState) -> list[str]:
    name_map = {"retriever": "retriever", "web": "web_search", "sql": "sql_agent", "code": "code_agent"}
    plan = state.get("plan", "")
    agents = [a.strip() for a in plan.split(",") if a.strip() in VALID_AGENTS]
    return [name_map[a] for a in agents] or ["retriever"]


def synthesize(state: AgentState) -> dict:
    llm = get_llm()

    documents_text = "\n\n".join(state.get("documents", [])) or "(none)"
    sql_text = state.get("sql_result") or "(none)"
    code_text = state.get("code_result") or "(none)"

    revision_note = ""
    if state.get("critique_feedback"):
        revision_note = REVISION_NOTE_TEMPLATE.format(
            previous_answer=state.get("answer", ""),
            feedback=state["critique_feedback"],
        )

    prompt = SYNTHESIS_PROMPT.format(
        question=state["question"],
        documents=documents_text,
        sql_result=sql_text,
        code_result=code_text,
        revision_note=revision_note,
        memory_block=_memory_block(state),
    )

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip()
    except Exception as e:
        answer = f"(synthesis error: {e})"

    label = "revised" if revision_note else "drafted"
    return {
        "answer": answer,
        "steps": [f"synthesizer: {label} answer"],
    }


if __name__ == "__main__":
    test_questions = [
        "Why do customers churn, according to our handbook?",
        "What is the current USD to UZS exchange rate?",
        "How many customers have churned in the last 90 days?",
        "What is the standard deviation of these numbers: 45, 67, 23, 89?",
    ]

    for q in test_questions:
        state = new_state(q)
        update = route(state)
        print(f"Question: {q}")
        print(f"  -> plan: {update['plan']}")
        print(f"  -> next nodes: {route_to_agents({**state, **update})}\n")
