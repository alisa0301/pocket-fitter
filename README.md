# Pocket Fitter

Since AI Hackathon project. Python (FastAPI) backend + React (Vite, TypeScript) frontend. AI agent sessions tracked with [Entire](https://docs.entire.io).

## Structure

```
backend/    FastAPI app (uv)
  app/main.py         app + CORS
  app/api/routes.py   /api/health, /api/chat
  app/services/       gemini.py (LLM), scripted.py (fallback)
  app/core/config.py  settings from .env
  tests/
frontend/   React + Vite + TS, proxies /api -> :8000
```

## Quick start

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
make install
cp backend/.env.example backend/.env
make backend    # http://localhost:8000/docs
make frontend   # http://localhost:5173
```

## Gemini

The chat endpoint (`POST /api/chat`) uses Gemini when `GEMINI_API_KEY` is set in `backend/.env`
(get one at https://aistudio.google.com/apikey); otherwise it runs a scripted demo flow.
Change the model with `GEMINI_MODEL`. Prompt lives in `backend/app/services/gemini.py`.

## Entire

Install the CLI (see https://docs.entire.io/platforms/cli), then in the repo root:

```bash
entire enable            # installs git hooks + agent hooks (e.g. --agent claude-code)
git add .entire && git commit -m "Enable Entire"
```

Checkpoints (agent transcripts + touched files) are stored on the `entire/checkpoints/v1` branch — push it too:

```bash
git push origin entire/checkpoints/v1
```
