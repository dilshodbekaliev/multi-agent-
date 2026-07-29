import io
import signal
import contextlib

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.state import AgentState, new_state
from app.tracing import get_langfuse_callbacks

CODE_PROMPT = """You are a Python expert. Write a short Python script that \
computes the answer to the question below, then prints ONLY the final \
result with print().

Rules:
- Output ONLY raw Python code. No markdown fences, no explanation.
- You may use these standard library modules only: math, statistics, \
datetime, re, json, itertools, collections, decimal.
- No file I/O, no network calls, no imports outside the allowed list, \
no input().
- End with a print() statement showing the final answer.

Question: {question}

Python code:"""

ALLOWED_MODULES = {"math", "statistics", "datetime", "re", "json", "itertools", "collections", "decimal"}
TIMEOUT_SECONDS = 5


def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        callbacks=get_langfuse_callbacks(),
    )


def generate_code(question: str) -> str:
    llm = get_llm()
    response = llm.invoke(CODE_PROMPT.format(question=question))
    code = response.content.strip()
    import re as _re
    code = _re.sub(r"^```(?:python)?\s*|\s*```$", "", code, flags=_re.IGNORECASE).strip()
    return code


def _restricted_import(name, *args, **kwargs):
    if name not in ALLOWED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in the code sandbox")
    return __import__(name, *args, **kwargs)


def _timeout_handler(signum, frame):
    raise TimeoutError(f"Code execution exceeded {TIMEOUT_SECONDS}s")


def run_sandboxed(code: str) -> str:
    safe_builtins = {
        "abs": abs, "round": round, "len": len, "sum": sum, "min": min, "max": max,
        "sorted": sorted, "range": range, "enumerate": enumerate, "zip": zip,
        "map": map, "filter": filter, "print": print, "float": float, "int": int,
        "str": str, "list": list, "dict": dict, "set": set, "tuple": tuple,
        "bool": bool, "__import__": _restricted_import,
    }
    sandbox_globals = {"__builtins__": safe_builtins}
    stdout_capture = io.StringIO()

    signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(TIMEOUT_SECONDS)
    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, sandbox_globals)
    finally:
        signal.alarm(0)

    return stdout_capture.getvalue().strip()


def code_agent_node(state: AgentState) -> dict:
    question = state["question"]

    try:
        code = generate_code(question)
    except Exception as e:
        return {
            "code_result": None,
            "steps": [f"code_agent: LLM error generating code — {e}"],
        }

    try:
        output = run_sandboxed(code)
    except Exception as e:
        return {
            "code_result": None,
            "steps": [f"code_agent: execution error — {e} (code: {code})"],
        }

    result_text = f"Code:\n{code}\n\nOutput:\n{output}"

    return {
        "code_result": result_text,
        "steps": ["code_agent: executed successfully"],
    }


if __name__ == "__main__":
    test_question = "What is the standard deviation of these order amounts: 45, 67, 23, 89, 12, 56, 78?"
    state = new_state(test_question)

    update = code_agent_node(state)

    print(f"Question: {test_question}\n")
    print("Steps:")
    for s in update["steps"]:
        print(" -", s)

    print("\nResult:")
    print(update["code_result"])
