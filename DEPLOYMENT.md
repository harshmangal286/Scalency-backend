# Deployment Guide

This document explains how to deploy **scalency-backend** in a production environment using Docker Compose.

---

## Prerequisites

| Tool | Minimum Version |
|---|---|
| Docker | 24+ |
| Docker Compose | v2 (bundled with Docker Desktop / Docker Engine) |
| A Linux VPS or cloud VM | 1 vCPU / 1 GB RAM minimum |

---

## Step 1 – Transfer Files to the Server

```bash
# Option A – git clone directly on the server
git clone <your-repo-url> /opt/scalency-backend
cd /opt/scalency-backend

# Option B – rsync from your local machine
rsync -avz ./ user@your-server:/opt/scalency-backend/
```

---

## Step 2 – Configure Environment Variables

```bash
cd /opt/scalency-backend
cp .env.example .env
nano .env   # or use your preferred editor
```

Set every variable:

```dotenv
DATABASE_URL=postgresql://postgres:STRONG_PASSWORD@postgres:5432/scalency
REDIS_URL=redis://redis:6379
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxxxxxx
SECRET_KEY=a-long-random-string-at-least-32-chars
```

> **Security notes**
> - Use a strong, unique `POSTGRES_PASSWORD` and update the `DATABASE_URL` accordingly.
> - Never commit `.env` to version control.
> - Rotate `SECRET_KEY` before going live.

---

## Step 3 – Update docker-compose for Production Passwords

Open `docker-compose.yml` and change the PostgreSQL credentials to match your `.env`:

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: STRONG_PASSWORD   # match DATABASE_URL
```

---

## Step 4 – Build and Start

```bash
docker-compose up --build -d
```

This command:
1. Builds the `api` and `worker` images from `Dockerfile`.
2. Pulls `postgres:15-alpine` and `redis:7-alpine`.
3. Starts all four services in the background.
4. The `api` service runs DB table creation on startup (via `create_tables()`).

---

## Step 5 – Verify Deployment

```bash
# Check all containers are running
docker-compose ps

# Tail combined logs
docker-compose logs -f

# Quick health check
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "version": "1.0.0", "database": "ok"}
```

---

## Step 6 – Reverse Proxy (Nginx / Caddy)

For external HTTPS access, put a reverse proxy in front of port 8000.

**Minimal Nginx config:**

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Use **Certbot** to provision a free TLS certificate:

```bash
sudo certbot --nginx -d api.yourdomain.com
```

---

## Step 7 – Scaling the Worker

To handle more background jobs, increase Celery concurrency or run additional worker replicas:

```bash
# Increase concurrency within a single container
docker-compose exec worker celery -A app.tasks.celery_worker.celery_app \
  worker --loglevel=info --concurrency=8

# Or scale to multiple worker containers
docker-compose up -d --scale worker=3
```

---

## Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart with zero-downtime rolling update
docker-compose up --build -d
```

---

## Stopping the Application

```bash
# Stop without removing data volumes
docker-compose stop

# Stop and remove containers (volumes retained)
docker-compose down

# Stop and remove containers AND data volumes (destructive)
docker-compose down -v
```

---

## Data Persistence

PostgreSQL data is stored in the named Docker volume `postgres_data`.
Back up regularly:

```bash
docker exec scalency_postgres pg_dump -U postgres scalency > backup_$(date +%F).sql
```

Restore:

```bash
cat backup_2026-03-08.sql | docker exec -i scalency_postgres psql -U postgres scalency
```

---

## Health Monitoring

Integrate the `/health` endpoint with any uptime monitoring service (e.g. UptimeRobot, Better Uptime, Grafana Cloud):

- URL: `https://api.yourdomain.com/health`
- Expected HTTP status: `200`
- Expected body contains: `"status": "ok"`

---

## Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| API exits immediately | Missing `.env` or wrong `DATABASE_URL` | Check `docker-compose logs api` |
| Worker not picking up tasks | Redis unreachable | Ensure Redis container is healthy |
| `psycopg2` connection error | Postgres not ready | Wait for healthcheck; the API waits automatically |
| AI endpoint returns 502 | Invalid or missing `OPENROUTER_API_KEY` | Set correct key in `.env` |
