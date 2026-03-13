# Scalency Backend - Commands Reference

Complete guide to useful commands for developing, managing, and deploying the Scalency backend.

## 🐳 Docker Compose Commands

### Start Services

```bash
# Start all services in background
docker compose up -d

# Start all services with logs visible
docker compose up

# Start specific service
docker compose up -d scalency_api

# Restart services
docker compose restart

# Stop services (keeps containers)
docker compose stop

# Stop and remove containers
docker compose down

# Remove everything including volumes (⚠️ deletes data)
docker compose down -v
```

### View Logs

```bash
# View logs from all services
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View logs from specific service
docker compose logs scalency_api
docker compose logs scalency_worker
docker compose logs scalency_postgres
docker compose logs scalency_redis

# View last 50 lines and follow
docker compose logs -f --tail=50 scalency_api

# View logs for multiple services
docker compose logs -f scalency_api scalency_worker
```

### Check Service Status

```bash
# Show status of all services
docker compose ps

# Show status with more details
docker compose ps -a

# Check if service is running
docker compose ps scalency_api
```

### Execute Commands in Containers

```bash
# Open shell in API container
docker compose exec scalency_api bash

# Open shell in worker container
docker compose exec scalency_worker bash

# Open PostgreSQL shell
docker compose exec scalency_postgres psql -U scalency -d scalency

# Open Redis CLI
docker compose exec scalency_redis redis-cli

# Run Python command in API container
docker compose exec scalency_api python -c "print('Hello')"
```

---

## 🗄️ Database Commands

### PostgreSQL Operations

```bash
# Connect to database
docker compose exec scalency_postgres psql -U scalency -d scalency

# Inside psql shell:
\dt                    # List all tables
\du                    # List users/roles
SELECT * FROM users;   # Query users table
\q                     # Exit

# Create database backup
docker compose exec scalency_postgres pg_dump -U scalency scalency > backup.sql

# Restore from backup
docker compose exec -T scalency_postgres psql -U scalency scalency < backup.sql

# Run SQL file
docker compose exec -T scalency_postgres psql -U scalency scalency < init.sql

# Delete all data (⚠️ careful!)
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "DROP TABLE IF EXISTS listings, users, jobs CASCADE;"
```

### Create Tables

```bash
# Tables auto-created on startup via entrypoint.sh
# To manually trigger:
docker compose exec scalency_api python -c \
  "from app.core.database import create_tables; create_tables()"
```

### Database Queries

```bash
# Check users count
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "SELECT COUNT(*) FROM users;"

# Check listings count
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "SELECT COUNT(*) FROM listings;"

# List all jobs
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "SELECT id, task_name, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 10;"

# Export listings to CSV
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "COPY listings(id, user_id, title, brand, category, price, status) TO STDOUT DELIMITER ',' CSV HEADER" > listings.csv
```

---

## 📦 Redis Commands

### Redis CLI Operations

```bash
# Open Redis CLI
docker compose exec scalency_redis redis-cli

# Inside redis-cli:
PING                   # Test connection
KEYS *                 # List all keys
DBSIZE                 # Total keys count
FLUSHDB                # Clear current database (⚠️)
FLUSHALL               # Clear all databases (⚠️)

# Check job queue
LLEN celery            # Length of celery queue
LRANGE celery 0 -1     # View all items in queue

# Monitor activity (real-time)
MONITOR

# Exit
EXIT
```

### Redis Information

```bash
# Get Redis server info
docker compose exec scalency_redis redis-cli INFO

# Get memory usage
docker compose exec scalency_redis redis-cli INFO memory

# Get replication status
docker compose exec scalency_redis redis-cli INFO replication

# Backup Redis
docker compose exec scalency_redis redis-cli BGSAVE
docker compose cp scalency_redis:/data/dump.rdb ./redis-backup.rdb

# Restore Redis
docker compose cp ./redis-backup.rdb scalency_redis:/data/dump.rdb
docker compose restart scalency_redis
```

---

## 🤖 Celery Worker Commands

### Monitor Celery Tasks

```bash
# View worker status
docker compose exec scalency_worker celery -A app.tasks.celery_worker inspect active

# List all available tasks
docker compose exec scalency_worker celery -A app.tasks.celery_worker inspect registered

# View task stats
docker compose exec scalency_worker celery -A app.tasks.celery_worker inspect stats

# Monitor in real-time (requires flower)
docker compose exec scalency_worker celery -A app.tasks.celery_worker events

# View task history
docker compose logs scalency_worker | grep "Task"
```

### Clear Task Queue

```bash
# Remove all pending tasks
docker compose exec scalency_worker celery -A app.tasks.celery_worker purge

# Restart worker (clears in-progress tasks)
docker compose restart scalency_worker
```

### Task Configuration

```bash
# Check worker configuration
docker compose exec scalency_worker celery -A app.tasks.celery_worker inspect active_queues

# Set concurrency (parallel workers)
docker compose exec scalency_worker celery -A app.tasks.celery_worker --concurrency=4 worker
```

---

## 🚀 API Server Commands

### Start/Stop API

```bash
# Start API only
docker compose up -d scalency_api

# Restart API
docker compose restart scalency_api

# View API logs
docker compose logs -f scalency_api

# Rebuild API image
docker compose build scalency_api

# Rebuild and restart
docker compose up -d --build scalency_api
```

### API Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check API Swagger docs
curl -s http://localhost:8000/docs | head -20

# Get OpenAPI schema
curl http://localhost:8000/openapi.json | jq .

# Test API endpoint
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

### API Debugging

```bash
# Log into API container bash
docker compose exec scalency_api bash

# Inside container, run Python shell
python -c "from app.main import app; print(app.routes)"

# Check environment variables
docker compose exec scalency_api env | grep -E "DATABASE|REDIS|OPEN"

# Run Python script
docker compose exec scalency_api python script.py
```

---

## 🔨 Development Commands

### Local Development (Without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost/scalency"
export REDIS_URL="redis://localhost:6379"
export OPENROUTER_API_KEY="your-api-key"

# Run API server
uvicorn app.main:app --reload --port 8000

# In another terminal, start Celery worker
celery -A app.tasks.celery_worker worker --loglevel=info
```

### Code Quality

```bash
# Format code (Black)
docker compose exec scalency_api black app/

# Lint code (Flake8)
docker compose exec scalency_api flake8 app/

# Type checking (Mypy)
docker compose exec scalency_api mypy app/

# Security check (Bandit)
docker compose exec scalency_api bandit -r app/
```

---

## 🛠️ Build & Deployment Commands

### Docker Image Operations

```bash
# Build API image
docker build -t scalency-api:latest .

# Build all images
docker compose build

# Rebuild specific service
docker compose build scalency_api

# Push to registry
docker tag scalency-api:latest your-registry/scalency-api:latest
docker push your-registry/scalency-api:latest

# View images
docker images | grep scalency
```

### Docker Compose File Validation

```bash
# Validate compose file
docker compose config

# Check for issues
docker compose config --quiet
```

---

## 🧪 Testing Commands

### Run Tests

```bash
# Run all tests
docker compose exec scalency_api pytest tests/

# Run specific test file
docker compose exec scalency_api pytest tests/test_users.py

# Run with coverage
docker compose exec scalency_api pytest --cov=app tests/

# Run specific test
docker compose exec scalency_api pytest tests/test_users.py::test_register_user

# Run with verbose output
docker compose exec scalency_api pytest -v tests/
```

### API Testing

```bash
# Test user registration
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# Test image file upload
curl -X POST http://localhost:8000/api/v1/listings/upload \
  -F "file=@/path/to/image.jpg"

# Test listing generation (requires valid image URL)
curl -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "image_url":"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
    "user_id":"<USER_ID>"
  }'

# Test pricing suggestion
curl -X POST http://localhost:8000/api/v1/pricing/suggest \
  -H "Content-Type: application/json" \
  -d '{"brand":"Apple","category":"phones","condition":"new"}'
```

---

## 📊 Monitoring & Debugging

### System Resource Usage

```bash
# View container resource usage
docker stats

# View specific container stats
docker stats scalency_api

# See CPU and memory
docker compose stats scalency_api scalency_postgres scalency_redis scalency_worker
```

### Network & Ports

```bash
# Check open ports
docker compose port

# Check port binding
netstat -tulpn | grep 8000
netstat -tulpn | grep 5432

# Test connectivity between containers
docker compose exec scalency_api ping scalency_postgres
docker compose exec scalency_api ping scalency_redis
```

### Environment & Configuration

```bash
# View environment variables
docker compose exec scalency_api env

# Check .env file
cat .env

# Verify variables loaded
docker compose exec scalency_api python -c "from app.core.config import settings; print(settings)"
```

---

## 🔄 Common Development Workflows

### Full Reset (Local Development)

```bash
# Stop everything
docker compose down -v

# Clean up
docker system prune -a --volumes

# Restart fresh
docker compose up -d

# Verify all services
docker compose ps
docker compose logs -f
```

### Debug a Failing Task

```bash
# Check worker logs
docker compose logs -f scalency_worker

# Check job status in database
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "SELECT * FROM jobs WHERE status='failed' LIMIT 1;"

# View Redis queue
docker compose exec scalency_redis redis-cli LRANGE celery 0 -1

# Restart worker
docker compose restart scalency_worker
```

### Check AI Service Integration

```bash
# View API logs for AI calls
docker compose logs scalency_api | grep -i "openrouter\|ai_service"

# Check if OpenRouter key is set
docker compose exec scalency_api python -c "import os; print(os.getenv('OPENROUTER_API_KEY'))"

# Test AI service directly
docker compose exec scalency_api python -c \
  "from app.services.ai_service import extract_attributes; print(extract_attributes('https://...'))"
```

### Migrate Data Between Environments

```bash
# Export from local
docker compose exec scalency_postgres pg_dump -U scalency scalency > backup-local.sql

# Import to another environment
cat backup-local.sql | docker compose exec -T scalency_postgres psql -U scalency scalency
```

---

## 🚨 Troubleshooting Commands

### Check Service Dependencies

```bash
# Verify all services are up
docker compose ps

# Check API can reach database
docker compose exec scalency_api python -c \
  "from app.core.database import SessionLocal; SessionLocal(); print('✓ DB OK')"

# Check API can reach Redis
docker compose exec scalency_api python -c \
  "import redis; redis.Redis.from_url('redis://scalency_redis:6379'); print('✓ Redis OK')"
```

### Fix Common Issues

```bash
# Port already in use
lsof -i :8000
kill -9 <PID>

# Database connection refused
docker compose restart scalency_postgres
sleep 5
docker compose exec scalency_postgres pg_isready

# Worker not processing tasks
docker compose restart scalency_worker
docker compose logs -f scalency_worker

# Clear all queues and restart
docker compose exec scalency_redis redis-cli FLUSHALL
docker compose restart
```

### View Detailed Error Information

```bash
# Full stack trace for failed task
docker compose logs scalency_worker | tail -100

# Full API error response
curl -v http://localhost:8000/api/v1/invalid-endpoint

# Database connection issues
docker compose logs scalency_postgres | grep -i "error\|failed"
```

---

## 📝 Useful One-Liners

```bash
# Quick health check
docker compose exec scalency_api curl -s http://localhost:8000/health | jq .

# Count active tasks
docker compose exec scalency_redis redis-cli LLEN celery

# List all users
docker compose exec scalency_postgres psql -U scalency -d scalency -c "SELECT COUNT(*) FROM users;"

# View recent errors
docker compose logs --tail=100 | grep -i error

# Restart everything quickly
docker compose down && sleep 2 && docker compose up -d && sleep 5 && docker compose ps

# Monitor all services in real-time
watch 'docker compose ps'

# Export all containers' logs
docker compose logs > full-logs-$(date +%s).txt
```

---

## 🔐 Security Commands

### Change Database Password

```bash
# Connect to database
docker compose exec scalency_postgres psql -U scalency -d scalency

# In psql:
ALTER USER scalency WITH PASSWORD 'new_password';
\q

# Update .env file
sed -i 's/DATABASE_PASSWORD=.*/DATABASE_PASSWORD=new_password/' .env

# Restart services
docker compose restart
```

### Reset API Keys

```bash
# Update OpenRouter API key
sed -i 's/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=new-key/' .env

# Restart API
docker compose restart scalency_api
```

### View Sensitive Information (⚠️ Be careful!)

```bash
# Show .env file (contains secrets!)
cat .env | grep -v "^#"

# Check if secrets are in logs (should not be!)
docker compose logs | grep -i "api_key\|password" | head -5
```

---

## 📈 Performance Tuning Commands

```bash
# Increase worker concurrency
docker compose exec scalency_worker celery -A app.tasks.celery_worker --concurrency=8 worker

# Check connection pool settings
docker compose exec scalency_api python -c \
  "from app.core.database import engine; print(engine.pool.size, engine.pool.max_overflow)"

# Monitor query performance
docker compose exec scalency_postgres psql -U scalency -d scalency \
  -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC;"
```

---

## 📚 Reference

For complete API documentation, see [API_GUIDE.md](./API_GUIDE.md)

For setup instructions, see [README.md](./README.md)

For deployment guides, see [DEPLOYMENT.md](./DEPLOYMENT.md)

---

**Last Updated:** March 2026
**Status:** ✅ Production Ready
