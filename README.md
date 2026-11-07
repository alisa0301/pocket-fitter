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

## MongoDB (optional)

Set `MONGODB_URI` (e.g. a MongoDB Atlas connection string) in `backend/.env`. Without it the app
reads the catalog from the bundled JSON and does not save fittings.

- `products` / `catalog_meta`: Takomo's iron catalog (5 heads, 35 shafts, 3 grips, length/lie
  options, fitting rules), loaded from `backend/app/data/takomo_products.json` by
  `cd backend && uv run python -m app.seed` (idempotent; re-run after updating the JSON).
  Served at `GET /api/products` and injected into the Gemini prompt.
- `fittings`: one document per chat session (messages, step, final recommendation). `POST /api/chat`
  returns a `fitting_id`; `GET /api/fittings/{id}` reads it back.

For Cloud Run, store the URI in Secret Manager as `mongodb-uri` and add
`MONGODB_URI=mongodb-uri:latest` to `secrets:` in `.github/workflows/deploy.yml`.

## Deploy (GitHub Actions -> Google Cloud Run)

Every push to `main` runs tests, builds one Docker image (React build served by FastAPI) and deploys it
to Cloud Run. GitHub authenticates to Google Cloud via Workload Identity Federation (no JSON keys);
the Gemini key lives in Secret Manager.

One-time setup (needs a GCP project with billing and `gcloud auth login` as Owner):

```bash
./scripts/gcp-setup.sh <PROJECT_ID>            # region defaults to europe-north1
```

Then add the variables it prints under GitHub -> Settings -> Secrets and variables -> Actions -> **Variables**,
and push to `main` (or run the workflow manually from the Actions tab). The service URL is printed in
the deploy job log and in the Cloud Run console.

Local container check: `docker build -t pocket-fitter . && docker run -p 8080:8080 -e GEMINI_API_KEY=... pocket-fitter`

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
