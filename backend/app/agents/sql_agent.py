import re
import sqlite3

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.state import AgentState, new_state
from app.tracing import get_langfuse_callbacks

SCHEMA = """
Table: customers
  customer_id INTEGER, name TEXT, country TEXT,
  signup_date TEXT (YYYY-MM-DD), is_churned INTEGER (1=churned, 0=active),
  churn_date TEXT (YYYY-MM-DD, NULL if not churned)

Table: products
  product_id INTEGER, name TEXT, category TEXT, unit_price REAL

Table: orders
  order_id INTEGER, customer_id INTEGER, product_id INTEGER,
  quantity INTEGER, order_date TEXT (YYYY-MM-DD)
"""

SQL_PROMPT = """You are a SQLite expert. Given the schema below and a question, \
write ONE read-only SQL query that answers it.

Schema:
{schema}

Rules:
- Output ONLY the raw SQL query. No markdown fences, no explanation, no semicolon-separated multiple statements.
- Only SELECT statements — never INSERT/UPDATE/DELETE/DROP.
- Use standard SQLite syntax (e.g. date('now') for the current date).

Question: {question}

SQL:"""


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        callbacks=get_langfuse_callbacks(),
    )


def generate_sql(question: str) -> str:
    llm = get_llm()
    prompt = SQL_PROMPT.format(schema=SCHEMA, question=question)
    response = llm.invoke(prompt)
    sql = response.content.strip()
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE).strip()
    return sql


def is_safe_select(sql: str) -> bool:
    normalized = sql.strip().rstrip(";").strip().lower()
    if not normalized.startswith("select"):
        return False
    forbidden = ["insert", "update", "delete", "drop", "alter", "attach", "pragma", ";"]
    body = sql.strip().rstrip(";")
    return not any(word in body.lower() for word in forbidden)


def execute_sql(sql: str, max_rows: int = 20):
    conn = sqlite3.connect(settings.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(max_rows)
        columns = [d[0] for d in cur.description] if cur.description else []
        return columns, [tuple(row) for row in rows]
    finally:
        conn.close()


def sql_agent_node(state: AgentState) -> dict:
    question = state["question"]

    try:
        sql = generate_sql(question)
    except Exception as e:
        return {
            "sql_result": None,
            "steps": [f"sql_agent: LLM error generating SQL — {e}"],
        }

    if not is_safe_select(sql):
        return {
            "sql_result": None,
            "steps": [f"sql_agent: blocked unsafe/non-SELECT query: {sql}"],
        }

    try:
        columns, rows = execute_sql(sql)
    except Exception as e:
        return {
            "sql_result": None,
            "steps": [f"sql_agent: SQL execution error — {e} (query: {sql})"],
        }

    result_text = f"SQL: {sql}\nColumns: {columns}\nRows: {rows}"

    return {
        "sql_result": result_text,
        "steps": [f"sql_agent: ran query, {len(rows)} row(s) returned"],
    }


if __name__ == "__main__":
    test_question = "How many customers have churned in the last 90 days?"
    state = new_state(test_question)

    update = sql_agent_node(state)

    print(f"Question: {test_question}\n")
    print("Steps:")
    for s in update["steps"]:
        print(" -", s)

    print("\nResult:")
    print(update["sql_result"])
