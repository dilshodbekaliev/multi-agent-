# Multi-Agent AI Analyst — Backend

Capstone project: a supervisor-led multi-agent system (retriever + web + SQL + code agents,
a critic, memory, evaluation, tracing). Built phase by phase per the project guide.

## Phase 1 — Foundation (done in this step)

- **F1** `app/config.py` + `app/state.py` — settings loaded from `.env`, shared `AgentState`.
- **F2** `app/ingestion.py` — loads docs from `docs/`, chunks, embeds with Gemini, stores in Qdrant.
- Sample DB for later: `data/create_db.py` generates `data/company.db` (customers/products/orders,
  ready for the F5 Text-to-SQL agent).
- Sample doc for later: `docs/company_handbook.txt`, ready for the F3 retriever agent.

## Setup

1. **Python env**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Get your Gemini key** (free, no card): https://aistudio.google.com/apikey

3. **Configure keys**
   ```bash
   cp .env.example .env
   # edit .env and paste your GOOGLE_API_KEY
   ```

4. **Check config loads correctly** (F1 "done when")
   ```bash
   python -m app.config
   ```
   Should print `Config loaded. LLM: gemini-2.5-flash` and flag any missing optional keys.

5. **Build the vector store** (F2 "done when": ingestion + similarity search works)
   ```bash
   python -m app.ingestion
   ```
   This embeds `docs/company_handbook.txt` into a local embedded Qdrant store
   (`data/qdrant_local/`, no signup needed) and runs a test similarity search.

6. **Sample DB already generated** — `data/company.db` exists (200 customers, 14 products,
   ~1300 orders). Regenerate anytime with `python data/create_db.py`.

## Phase 1 checklist (matches guide's "Done when")

- [x] `AgentState` TypedDict defined, used as the single shared object
- [x] Keys load from `.env` via `config.py`
- [x] Document ingested, chunked (1000/150), embedded, stored in Qdrant
- [x] Similarity search returns relevant chunks
- [x] `revisions` field present in state so the graph can terminate later (F9)
- [x] `.env` is gitignored — never commit real keys

## Next: Phase 2 — Specialist agents (F3–F6)

Build and test one at a time: retriever agent (F3) → web agent (F4) →
data/SQL agent (F5, using `data/company.db`) → code agent (F6).
