FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime libraries for psycopg and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libjpeg62-turbo \
    libwebp7 \
    libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dev/test tools (ruff, pytest) are included so `docker compose run --rm web pytest` works.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# Ensure media and static dirs exist
RUN mkdir -p /app/media /app/private_media /app/staticfiles

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000"]
