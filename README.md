# Multi-Agent AI Analyst

A supervisor-led multi-agent system that answers business questions by routing them to the right specialist agent — internal document search, live web search, SQL database queries, or Python code execution — then synthesizes and fact-checks the result before responding.

**[Live demo →](https://multi-agent-taupe.vercel.app)**

![faithfulness](https://img.shields.io/badge/faithfulness-0.96-brightgreen) ![answer relevancy](https://img.shields.io/badge/answer_relevancy-0.99-brightgreen)

---

## What it does

Ask a question in plain English — about customer/order data, company policy, current events, or a calculation — and the system:

1. **Routes** it to the right specialist agent(s), running them in parallel when a question spans multiple sources
2. **Gathers evidence** from a vector store, a SQL database, live web search, or a sandboxed Python execution
3. **Synthesizes** a grounded answer from that evidence only
4. **Critiques** its own answer against the evidence, and revises if it finds unsupported claims
5. **Remembers** the conversation across turns, so follow-up questions work naturally

Every step streams live to the UI as it happens.

## Architecture

```
                    ┌──────────────┐
        question →  │  Supervisor  │  (routes based on question type)
                    └──────┬───────┘
                           │ fan-out (parallel)
       ┌─────────┬─────────┼─────────┬─────────┐
       ▼         ▼         ▼         ▼
  Retriever   Web Search  SQL Agent  Code Agent
  (vector DB)  (Tavily)   (text-to-SQL) (sandboxed exec)
       │         │         │         │
       └─────────┴────┬────┴─────────┘
                       ▼
                 Synthesizer
                       │
                       ▼
                    Critic  ──fail──► (revise, up to N times)
                       │
                      pass
                       ▼
                    Answer
```

State flows through the graph via a shared, typed state object with concurrency-safe reducers, so parallel agent branches merge correctly instead of conflicting.

## Features

- **Multi-agent orchestration** (LangGraph) — dynamic routing, parallel execution, fan-in synthesis
- **Retrieval-augmented generation** — document ingestion, chunking, vector search (Qdrant)
- **Text-to-SQL agent** — natural language to safe, read-only SQL, with query validation
- **Sandboxed code execution agent** — restricted builtins, module allowlist, execution timeout
- **Web search fallback** — for questions outside the internal knowledge base
- **Self-correcting critic** — reviews every answer against its evidence before it's shown to the user, with a bounded revision loop
- **Persistent conversation memory** — SQLite-backed, with automatic summarization of older turns to keep context lean
- **Full observability** — every LLM call across every agent is traced (Langfuse), including full prompts, latency, and cost
- **Automated evaluation** — RAGAS-based faithfulness and answer-relevancy scoring against a held-out test set
- **Streaming UI** — Server-Sent Events pipe each agent's progress to the frontend in real time

## Tech stack

| Layer | Tech |
|---|---|
| Orchestration | LangGraph |
| LLM | Gemini (via `langchain-google-genai`) |
| Vector store | Qdrant |
| Database | SQLite |
| Web search | Tavily |
| Evaluation | RAGAS |
| Observability | Langfuse |
| Backend | FastAPI |
| Frontend | Next.js, React |
| Deployment | Render (API) + Vercel (frontend) |

## Evaluation results

Scored with RAGAS against a held-out test set covering document retrieval, SQL, and code-execution paths:

| Metric | Score |
|---|---|
| Faithfulness | 0.96 |
| Answer relevancy | 0.99 |

Faithfulness measures whether every claim in an answer is actually supported by the evidence gathered. Answer relevancy measures whether the answer actually addresses the question asked. Live scores are visible in the app's **Evaluation** tab.

## Running locally

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your own API keys — see .env.example for what's needed
python -m app.ingestion
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Requires your own API keys for Gemini (required) and optionally Tavily, Langfuse. Never commit a real `.env` file — see `.gitignore`.

## Project structure

```
backend/
  app/
    agents/       # retriever, web search, SQL, code, supervisor, critic
    config.py     # settings, loaded from environment
    state.py      # shared graph state
    graph.py      # LangGraph wiring
    memory.py     # conversation persistence + summarization
    tracing.py    # Langfuse integration
    eval.py       # RAGAS evaluation suite
    main.py       # FastAPI app
frontend/
  app/
    page.tsx      # chat + evaluation UI
```

## License

MIT
