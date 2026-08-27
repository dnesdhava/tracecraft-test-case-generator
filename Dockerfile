FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY config ./config
COPY src ./src

RUN pip install --no-cache-dir uv==0.12.5 \
    && uv sync --locked --no-dev \
    && rm -rf /root/.cache

ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["sh", "-c", "exec .venv/bin/gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 120 'tcg.interfaces.web.app:create_app()'"]