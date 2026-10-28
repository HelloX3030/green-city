FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

ENV PATH="/app/.venv/bin:$PATH" \
    GREENCITY_DB_PATH=/data/reports.db \
    GREENCITY_HISTORY_PATH=/data/history.json

RUN mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "if [ ! -f \"$GREENCITY_HISTORY_PATH\" ]; then cp history.json \"$GREENCITY_HISTORY_PATH\"; fi; exec uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning"]
