# ---------------------------------------------------------------------------
# Stage 1 – dependency installer (keeps the final image lean)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system build tools required by psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt


# ---------------------------------------------------------------------------
# Stage 2 – production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Strip Windows CRLF line endings (safe no-op on files already in LF format)
# and make the script executable.
RUN sed -i 's/\r//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

# entrypoint.sh waits for Postgres, runs create_tables() once, then starts Uvicorn.
# Running DDL here (before workers fork) eliminates all CREATE TABLE race conditions.
CMD ["./entrypoint.sh"]
