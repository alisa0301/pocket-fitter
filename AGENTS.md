# Notes for AI coding agents

- Backend: FastAPI in `backend/` (Python, managed with `uv`). API routes live in `backend/app/api/routes.py`, all under `/api`.
- Frontend: React + Vite + TypeScript in `frontend/`. Dev server proxies `/api` to `http://localhost:8000`.
- Run `make test` before committing.
- Agent sessions are tracked with Entire (`entire enable`); commit often so checkpoints stay small and readable.
