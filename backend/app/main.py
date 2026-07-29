import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.graph import build_graph
from app.state import new_state
from app.memory import init_db, save_turn, get_memory_context

app = FastAPI(title="Multi-Agent AI Analyst")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app_graph = build_graph()


@app.on_event("startup")
def ensure_vector_store_populated():
    """
    On platforms with ephemeral disks (e.g. Render free tier), the local
    Qdrant store resets on every deploy/restart. Auto-ingest the sample
    docs if the collection is empty, so the retriever agent (F3) always
    has something to search without a manual step.
    """
    try:
        from app.ingestion import get_qdrant_client, ensure_collection, build_vectorstore

        client = get_qdrant_client()
        ensure_collection(client)
        count = client.count(collection_name=settings.QDRANT_COLLECTION).count
        if count == 0:
            print("Vector store empty — running ingestion...")
            build_vectorstore()
        else:
            print(f"Vector store already has {count} point(s) — skipping ingestion.")
    except Exception as e:
        print(f"Startup ingestion check failed (non-fatal): {e}")


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    steps: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    memory_context = get_memory_context(req.session_id)
    state = new_state(req.question, memory_context=memory_context)

    result = app_graph.invoke(state)

    save_turn(req.session_id, req.question, result.get("answer", ""))

    return ChatResponse(answer=result.get("answer", ""), steps=result.get("steps", []))


@app.get("/chat/stream")
def chat_stream(question: str, session_id: str = "default"):
    def event_generator():
        memory_context = get_memory_context(session_id)
        state = new_state(question, memory_context=memory_context)

        final_answer = ""
        all_steps: list[str] = []

        for update in app_graph.stream(state):
            for _node_name, node_output in update.items():
                new_steps = node_output.get("steps", [])
                for step in new_steps:
                    all_steps.append(step)
                    yield f"event: step\ndata: {json.dumps({'step': step})}\n\n"
                if "answer" in node_output:
                    final_answer = node_output["answer"]

        save_turn(session_id, question, final_answer)

        yield f"event: done\ndata: {json.dumps({'answer': final_answer, 'steps': all_steps})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
