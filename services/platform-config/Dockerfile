FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONPATH=/app/lib \
    PRAAM_PLATFORM_ROOT=/app

COPY pyproject.toml uv.lock ./
COPY lib/praam_platform /app/lib/praam_platform

RUN uv sync --frozen --no-dev --extra api --no-editable

COPY services/platform-config/app /app/app
COPY services.yaml /app/services.yaml

EXPOSE 8080

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
