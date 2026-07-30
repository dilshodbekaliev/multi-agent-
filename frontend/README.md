# Frontend — Multi-Agent AI Analyst

Next.js chat interface for the Multi-Agent AI Analyst backend. Streams live agent execution as it happens (via Server-Sent Events), then renders the final answer alongside a per-question evaluation view.

See the [root README](../README.md) for the full project overview, architecture diagram, and live demo link.

## Setup

```bash
npm install
```

Create a `.env.local` file:

```bash
cp .env.local.example .env.local
```

| Variable | Required | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | No | Base URL of the backend API. Defaults to `http://localhost:8000` if unset, so local development works with no configuration. Set this to your deployed backend URL (e.g. a Render URL) when deploying. |

## Running

```bash
npm run dev
```

Runs at `http://localhost:3000`. Requires the backend to be running separately (see the backend README) — defaults to expecting it at `http://localhost:8000`.

## Features

- **Chat tab** — ask a question, watch each agent's progress stream in live as a connected trace log, then see the synthesized answer rendered as a distinct "report" card
- **Evaluation tab** — displays the most recent RAGAS evaluation results (faithfulness, answer relevancy) per test question, served from the backend's `/eval` endpoint
- **Conversation history** — earlier turns in the session remain visible, collapsed beneath the current exchange

## Design

The interface deliberately splits into two visual modes tied to what's actually happening: a dark, monospace **console** for the live agent trace (each step rendered as a connected node, colored by outcome — teal for a normal step, green for a passing critic review, amber for a failed one triggering revision), handing off to a warm, light **report card** for the finished answer. Typography pairs Space Grotesk (headings), Inter (body), and IBM Plex Mono (the trace log and technical labels).

## Project structure

```
app/
  layout.tsx      # fonts, metadata
  globals.css      # design tokens (CSS custom properties), animations
  page.tsx         # chat + evaluation views, SSE client
```

## How streaming works

The Chat tab opens an `EventSource` connection to the backend's `/chat/stream` endpoint. The backend emits a `step` event each time an agent finishes (supervisor routing, an individual specialist agent, the synthesizer, the critic), and a final `done` event with the complete answer. The UI appends each step to the trace log as it arrives rather than waiting for the full response.

## Deployment

Deployed on Vercel with the project root set to this `frontend` directory and `NEXT_PUBLIC_API_URL` set to the deployed backend's URL. No other configuration required — Vercel auto-detects the Next.js framework.
