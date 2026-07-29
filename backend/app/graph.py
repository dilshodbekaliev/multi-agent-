from langgraph.graph import StateGraph, START, END

from app.state import AgentState, new_state
from app.agents.supervisor import route, route_to_agents, synthesize
from app.agents.retriever import retriever_node
from app.agents.web_search import web_search_node
from app.agents.sql_agent import sql_agent_node
from app.agents.code_agent import code_agent_node
from app.agents.critic import critic_node

AGENT_NODES = ["retriever", "web_search", "sql_agent", "code_agent"]
MAX_REVISIONS = 2


def after_critic(state: AgentState) -> str:
    if state.get("critique_passed"):
        return "end"
    if state.get("revisions", 0) >= MAX_REVISIONS:
        return "end"
    return "revise"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", route)
    graph.add_node("retriever", retriever_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("sql_agent", sql_agent_node)
    graph.add_node("code_agent", code_agent_node)
    graph.add_node("synthesizer", synthesize)
    graph.add_node("critic", critic_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_to_agents, AGENT_NODES)

    for node in AGENT_NODES:
        graph.add_edge(node, "synthesizer")

    graph.add_edge("synthesizer", "critic")
    graph.add_conditional_edges("critic", after_critic, {"revise": "synthesizer", "end": END})

    return graph.compile()


if __name__ == "__main__":
    app_graph = build_graph()

    test_questions = [
        "Why do customers churn, according to our handbook?",
        "How many customers have churned in the last 90 days?",
    ]

    for q in test_questions:
        print("=" * 70)
        print(f"Question: {q}\n")

        result = app_graph.invoke(new_state(q))

        print("Steps:")
        for s in result["steps"]:
            print(" -", s)

        print(f"\nAnswer:\n{result['answer']}\n")
