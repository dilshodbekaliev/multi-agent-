"""
Interactive CLI: a real multi-turn conversation, backed by SQLite memory
(app/memory.py) and the full agent graph (app/graph.py).

Run:
    python -m app.chat

Type 'exit' to quit. Memory persists across restarts — ask something,
quit, run it again, and it'll still remember (same session_id).
"""
from app.graph import build_graph
from app.state import new_state
from app.memory import init_db, save_turn, get_memory_context

SESSION_ID = "default"  # single persistent session for this CLI


def main():
    init_db()
    app_graph = build_graph()

    print("Multi-Agent AI Analyst — type 'exit' to quit.\n")

    prior_context = get_memory_context(SESSION_ID)
    if prior_context:
        print("(Resuming a previous conversation — memory loaded.)\n")

    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        memory_context = get_memory_context(SESSION_ID)
        state = new_state(question, memory_context=memory_context)

        result = app_graph.invoke(state)

        print(f"\nAssistant: {result['answer']}\n")
        print("  [steps: " + " -> ".join(result["steps"]) + "]\n")

        save_turn(SESSION_ID, question, result["answer"])


if __name__ == "__main__":
    main()
