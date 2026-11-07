# --- Build the React frontend ---
FROM node:22-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Python backend serving API + static frontend ---
FROM python:3.13-slim
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH" STATIC_DIR=/app/static PORT=8080
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
COPY backend/app ./app
COPY --from=frontend /frontend/dist ./static
RUN useradd --uid 1000 app && chown -R app /app
USER app
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
