FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY src/ ./src/

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
WORKDIR /app/src
CMD ["sh", "-c", "python -m memory.init_memory && exec python server.py"]