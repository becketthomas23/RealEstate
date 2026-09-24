FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000
WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
COPY backend/src ./src
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev
COPY --from=frontend-build /app/frontend/out ./src/backend/static

CMD ["sh", "-c", "uv run uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT"]
