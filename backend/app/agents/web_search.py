from app.config import settings
from app.state import AgentState, new_state

MAX_RESULTS = 3


def web_search_node(state: AgentState) -> dict:
    question = state["question"]

    if not settings.TAVILY_API_KEY:
        return {
            "documents": [],
            "steps": ["web_search: skipped — TAVILY_API_KEY not set"],
        }

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(
            query=question,
            max_results=MAX_RESULTS,
            search_depth="advanced",
        )
        results = response.get("results", [])
    except Exception as e:
        return {
            "documents": [],
            "steps": [f"web_search: error — {e}"],
        }

    new_chunks = [
        f"[Web: {r.get('title', 'untitled')}] ({r.get('url', '')})\n{r.get('content', '')}"
        for r in results
    ]

    return {
        "documents": new_chunks,
        "steps": [f"web_search: found {len(new_chunks)} result(s)"],
    }


def needs_web_search(state: AgentState, min_docs: int = 2) -> bool:
    return len(state.get("documents", [])) < min_docs


if __name__ == "__main__":
    test_question = "What is the current USD to UZS exchange rate today?"
    state = new_state(test_question)

    update = web_search_node(state)

    print(f"Question: {test_question}\n")
    print("Steps:")
    for s in update["steps"]:
        print(" -", s)

    print(f"\nRetrieved {len(update['documents'])} result(s):")
    for i, doc in enumerate(update["documents"], 1):
        print(f"\n[{i}] {doc[:300]}...")
