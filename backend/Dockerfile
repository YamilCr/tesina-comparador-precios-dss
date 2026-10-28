FROM mcr.microsoft.com/playwright/python:v1.64.1-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY scripts ./scripts

RUN pip install --no-cache-dir "uv>=0.5,<1.0" && \
    uv pip install --system ".[browser]"

RUN chmod +x scripts/start_api.sh

EXPOSE 10000

CMD ["./scripts/start_api.sh"]
