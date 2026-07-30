# Multi-Agent AI Analyst

A supervisor-led multi-agent system that answers business questions by routing them to the right specialist — a document retriever, a live web search agent, a text-to-SQL agent, and a Python code agent — then self-critiques and revises its own answer before returning it. Built as a capstone project for the IT Park Uzbekistan × World Bank "Uzbekistan Digital Inclusion" AI/ML traineeship.

**Live demo:** https://multi-agent-taupe.vercel.app


> Free-tier hosting note: the backend runs on Render's free plan, which spins down after inactivity — the first request after a while may take 30–60 seconds to wake up.

---

## What it does

Ask a question in plain English — about company policy, customer/order data, current events, or a quick calculation — and the system:

1. **Routes** it to whichever specialist agent(s) can actually answer it (possibly more than one, in parallel)
2. **Gathers evidence** from internal documents, the live web, a SQL database, or sandboxed Python execution
3. **Drafts an answer** grounded only in that evidence
4. **Critiques itself** — checks the draft against the evidence and the question, and revises if it finds unsupported claims or an incomplete answer
5. **Remembers the conversation** — follow-up questions resolve correctly using persistent memory
6. **Streams every step live** to the UI as it happens, then hands off to a final answer

## Architecture

```
                         ┌──────────────┐
   question ──────────▶  │  supervisor  │  (routes to 1+ agents)
                         └──────┬───────┘
              ┌──────────┬──────┴──────┬──────────┐
              ▼          ▼             ▼          ▼
        ┌──────────┐┌─────────┐┌────────────┐┌───────────┐
        │retriever ││   web   ││  sql_agent ││ code_agent│
        │ (Qdrant) ││(Tavily) ││ (SQLite)   ││(sandboxed)│
        └────┬─────┘└────┬────┘└─────┬──────┘└─────┬─────┘
              └──────────┴──────┬────┴─────────────┘
                                 ▼
                          ┌─────────────┐
                          │ synthesizer │  (drafts answer from evidence)
                          └──────┬──────┘
                                 ▼
                          ┌─────────────┐   FAIL, revisions < cap
                          │   critic    │───────────┐
                          └──────┬──────┘           │
                             PASS or cap reached     │
                                 ▼                   │
                               answer ◀───────────────┘
```

All agents share one `AgentState` object that flows through the graph. `documents` and `steps` use LangGraph's `operator.add` reducer so parallel branches (e.g. retriever + web running together) merge safely instead of conflicting.

## Features

| # | Feature | Status |
|---|---|---|
| F1 | Shared state (`AgentState`) + config loaded from `.env` | ✅ |
| F2 | Document ingestion → chunking → embedding → Qdrant vector store | ✅ |
| F3 | Retriever agent (internal company documents) | ✅ |
| F4 | Web search agent (Tavily, `search_depth="advanced"`) | ✅ |
| F5 | Text-to-SQL agent (Gemini → SQLite, read-only `SELECT`-only guard) | ✅ |
| F6 | Code agent (Gemini-generated Python, sandboxed execution, 5s timeout) | ✅ |
| F7 | Supervisor: LLM router + parallel fan-out/fan-in graph + synthesizer | ✅ |
| F8 | Critic + revision loop (self-correction, capped retries) | ✅ |
| F9/F10 | Persistent conversation memory (SQLite, running summary + recent turns) | ✅ |
| F11 | RAGAS evaluation suite (faithfulness, answer relevancy) | ✅ |
| F12 | Langfuse tracing (every LLM call across every agent) | ✅ |
| F13 | FastAPI backend (SSE streaming) + Next.js frontend (live agent trace UI) | ✅ |
| F14 | Deployed: Vercel (frontend) + Render (backend) | ✅ |

## Tech stack

- **LLM:** Google Gemini (`gemini-flash-latest`), via `langchain-google-genai`
- **Embeddings:** `gemini-embedding-001` (3072-dim)
- **Orchestration:** LangGraph (`StateGraph`, parallel fan-out/fan-in, conditional revision loop)
- **Vector store:** Qdrant (local embedded mode)
- **Structured data:** SQLite (sample customers/orders/products dataset)
- **Web search:** Tavily
- **Evaluation:** RAGAS
- **Observability:** Langfuse
- **Backend:** FastAPI, Server-Sent Events for live streaming
- **Frontend:** Next.js (App Router), TypeScript
- **Hosting:** Render (backend), Vercel (frontend)

## Project structure

```
backend/
  app/
    agents/
      retriever.py       # F3
      web_search.py       # F4
      sql_agent.py         # F5
      code_agent.py        # F6
      supervisor.py         # F7 (router + synthesizer)
      critic.py              # F8
    config.py             # F1
    state.py               # F1
    ingestion.py             # F2
    memory.py                 # F9/F10
    tracing.py                 # F12
    graph.py                     # F7/F8 wiring (the compiled StateGraph)
    main.py                       # F13 (FastAPI app)
    chat.py                        # CLI chat client
    eval.py                         # F11
  data/
    create_db.py           # generates the sample SQLite dataset
    company.db              # 200 customers, 14 products, ~1300 orders
  docs/
    company_handbook.txt   # sample document for the retriever agent
frontend/
  app/
    page.tsx              # chat UI: live trace panel + report card
    layout.tsx
    globals.css
render.yaml                 # Render deployment config
DEPLOYMENT.md                 # step-by-step deploy guide
```

## Running locally

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GOOGLE_API_KEY at minimum
python -m app.ingestion   # builds the vector store
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`.

**Environment variables** (`backend/.env`):

| Variable | Required | Purpose |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Gemini API access |
| `TAVILY_API_KEY` | No | Web search agent (F4) — skips gracefully if unset |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | No | Tracing (F12) — disabled if unset |
| `FRONTEND_URL` | Deploy only | Allowed CORS origin in production |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md). Summary: Render deploys the backend from `render.yaml` (auto-ingests the vector store on startup, since Render's disk resets on every deploy); Vercel deploys the frontend from the `frontend/` directory with `NEXT_PUBLIC_API_URL` pointed at the Render URL.

## Notes on running the eval suite

`ragas` (as of the version available at build time) has a startup bug: it unconditionally imports `ChatVertexAI` from a `langchain_community` path that newer `langchain-community` releases have removed, even though this project never uses Vertex AI. If `python -m app.eval` fails with `ModuleNotFoundError: No module named 'langchain_community.chat_models.vertexai'`, it's patched with a small compatibility shim rather than a code change — see the project's setup notes for the exact fix.

## Known limitations

- SQLite data and the local Qdrant store reset on every Render redeploy (acceptable for a demo; would use managed Postgres + Qdrant Cloud for production persistence).
- Gemini's free tier caps at 20 requests/day per project — fine for demo use, would need a paid tier for real usage.
- Render's free tier spins down after inactivity, causing a cold-start delay on the first request.

## Author

Dilshodbek Aliev — B.Sc. Economics with Data Science, Westminster International University in Tashkent. Built as part of the IT Park Uzbekistan × World Bank AI/ML traineeship.
