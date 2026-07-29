from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import settings
from app.state import AgentState, new_state
from app.ingestion import get_qdrant_client, get_embeddings
from langchain_qdrant import QdrantVectorStore

TOP_K = 4


def get_retriever(k: int = TOP_K):
    client = get_qdrant_client()
    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=get_embeddings(),
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


def retriever_node(state: AgentState) -> dict:
    question = state["question"]

    try:
        retriever = get_retriever()
        results = retriever.invoke(question)
    except (UnexpectedResponse, ValueError) as e:
        return {
            "documents": [],
            "steps": [f"retriever: no results — has `python -m app.ingestion` been run? ({e})"],
        }

    new_chunks = [doc.page_content for doc in results]

    return {
        "documents": new_chunks,
        "steps": [f"retriever: found {len(new_chunks)} chunk(s)"],
    }


if __name__ == "__main__":
    test_question = "Why do customers churn, and how does the company respond?"
    state = new_state(test_question)

    update = retriever_node(state)

    print(f"Question: {test_question}\n")
    print("Steps:")
    for s in update["steps"]:
        print(" -", s)

    print(f"\nRetrieved {len(update['documents'])} chunk(s):")
    for i, doc in enumerate(update["documents"], 1):
        print(f"\n[{i}] {doc[:300]}...")
