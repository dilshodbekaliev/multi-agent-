# Backend — Multi-Agent AI Analyst

FastAPI service exposing a LangGraph-orchestrated multi-agent system: a supervisor routes each question to one or more specialist agents (document retrieval, SQL, web search, code execution), which run in parallel where applicable, before a synthesizer drafts an answer and a critic reviews it for factual grounding.

See the [root README](../README.md) for the full project overview, architecture diagram, and live demo link.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy the environment template and fill in your own keys:

```bash
cp .env.example .env
```

| Variable | Required | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API key ([get one free](https://aistudio.google.com/apikey)) |
| `TAVILY_API_KEY` | No | Enables the web search agent; skipped gracefully if unset |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | No | Enables LLM call tracing; disabled if unset |
| `QDRANT_URL` / `QDRANT_API_KEY` | No | Point at Qdrant Cloud instead of the default local embedded store |
| `DATABASE_PATH` | No | Path to the SQLite database used by the SQL agent (defaults to `./data/company.db`) |
| `FRONTEND_URL` | No | Additional CORS-allowed origin for a deployed frontend |

Never commit a real `.env` file — it's gitignored by default.

## Running

```bash
# Build the vector store (one-time, or after adding docs to docs/)
python -m app.ingestion

# Start the API
uvicorn app.main:app --reload --port 8000
```

The API auto-ingests the vector store on startup if it's found empty, so this also works correctly on platforms with ephemeral disks (e.g. a fresh Render deploy).

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Liveness check |
| `/chat` | POST | Run a full turn, returns `{answer, steps}` |
| `/chat/stream` | GET | Server-Sent Events stream of each agent step, then a final answer |
| `/eval` | GET | Returns the most recent saved evaluation results, if any |

## Project structure

```
app/
  config.py           # settings, loaded from environment
  state.py             # shared graph state (with concurrency-safe reducers)
  ingestion.py          # document loading, chunking, embedding, vector store
  memory.py            # SQLite conversation persistence + summarization
  tracing.py            # Langfuse callback wiring
  graph.py             # LangGraph construction (routing, fan-out/fan-in, critic loop)
  eval.py              # RAGAS evaluation suite
  main.py              # FastAPI app
  agents/
    retriever.py        # vector search over ingested documents
    web_search.py        # live web search fallback (Tavily)
    sql_agent.py          # natural language → validated read-only SQL
    code_agent.py          # sandboxed Python execution for calculations
    supervisor.py          # routing + answer synthesis
    critic.py             # answer review + revision trigger
data/
  create_db.py          # generates the sample SQLite dataset
docs/
  company_handbook.txt    # sample document for the retriever agent
```

## Testing an agent in isolation

Every agent module can be run standalone against a fixed test question, without going through the full graph:

```bash
python -m app.agents.retriever
python -m app.agents.sql_agent
python -m app.agents.code_agent
python -m app.agents.web_search
python -m app.agents.supervisor
python -m app.agents.critic
```

## Running the evaluation suite

```bash
python -m app.eval
```

Runs a fixed set of test questions through the full graph and scores the results with RAGAS (faithfulness, answer relevancy). Results are saved to `data/eval_results.json` and served via `GET /eval`. Note: this makes multiple LLM calls per question and can take several minutes on free-tier API rate limits.

## Design notes

- **Concurrency-safe state.** `AgentState.documents` and `AgentState.steps` use `Annotated[List, operator.add]` reducers so that parallel agent branches (e.g. retriever + web search running together) merge safely instead of raising a LangGraph state-conflict error. Every agent returns only its *new* items for these fields, not the full accumulated list.
- **Bounded self-correction.** The critic can send an answer back for revision, but is capped (`MAX_REVISIONS` in `graph.py`) to guarantee termination.
- **Sandboxed code execution.** The code agent restricts builtins, allows only a fixed set of standard library modules, and enforces an execution timeout — LLM-generated code is never executed with full Python access.
- **Graceful degradation.** Optional integrations (web search, tracing) are designed to no-op cleanly if their API keys aren't configured, rather than breaking the pipeline.
