# Scalency Backend

AI-assisted resale marketplace backend powered by **FastAPI**, **PostgreSQL**, **Celery + Redis**, and **AI Services** (OpenRouter + Claude).
Automates listing creation, AI-generated copy, intelligent pricing, background publishing, and reposting.

---

## 📚 Documentation Quick Links

| Document | Purpose |
|----------|---------|
| **[API_GUIDE.md](./API_GUIDE.md)** | 📖 Complete API endpoint documentation with examples |
| **[COMMANDS.md](./COMMANDS.md)** | 🛠️ Commands reference for Docker, Database, Celery, and Development |
| **[README.md](./README.md)** | 🏠 This file - Setup and architecture overview |
| **[DEPLOYMENT.md](./DEPLOYMENT.md)** | 🚀 Production deployment guides |

### Quick Navigation
- **Just starting?** → Read **Setup** section below, then [API_GUIDE.md](./API_GUIDE.md)
- **Need a command?** → Check [COMMANDS.md](./COMMANDS.md)
- **Want API docs?** → Visit http://localhost:8000/docs (after running locally)
- **Ready to deploy?** → See [DEPLOYMENT.md](./DEPLOYMENT.md)

---

## Features

| Feature | Description |
|---|---|
| AI Listing Generation | Send a product image URL → receive title, description, hashtags, brand, category |
| AI Price Suggestion | Rule-based price range from brand, category, and condition |
| Listing CRUD | Create and manage product listings |
| Background Publishing | Publish listings asynchronously via Celery |
| Auto-Repost | Automatically clone and republish listings when stock remains after a sale |
| Stock Management | Decrement stock; trigger repost when units remain |
| Job Tracking | Every background operation is tracked in `AutomationJob` |

---

## Technology Stack

- **FastAPI** – async REST API
- **SQLAlchemy 2 + PostgreSQL** – ORM and database
- **Celery + Redis** – distributed background job processing
- **OpenRouter API** – multi-model AI gateway
- **Docker / docker-compose** – containerisation

---

## ⚡ Quick Start

### Prerequisites
- Docker & Docker Compose
- **At least one AI service key:**
  - OpenRouter API key (free at https://openrouter.ai) - RECOMMENDED, cheaper
  - OR Claude API key (from https://console.anthropic.com/)

### Start Backend in 2 Minutes

```bash
# 1. Clone and navigate
cd scalency-backend

# 2. Set up environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Start all services
docker compose up -d

# 4. Verify it's running
curl http://localhost:8000/health
# Output: {"status":"ok"}

# 5. Access API docs
# Swagger UI: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc
```

### Test a Complete Flow

**Option A: Using an external image URL**

```bash
# 1. Register user
USER=$(curl -s -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
USER_ID=$(echo $USER | jq -r .id)

# 2. Generate listing from image
curl -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"image_url\":\"https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400\",
    \"user_id\":\"$USER_ID\"
  }"

# See response with AI-generated title, description, price suggestion, etc.
```

**Option B: Upload a local image file**

```bash
# 1. Register user
USER=$(curl -s -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}')
USER_ID=$(echo $USER | jq -r .id)

# 2. Upload image file
UPLOAD=$(curl -s -X POST http://localhost:8000/api/v1/listings/upload \
  -F "file=@/path/to/your/image.jpg")
IMAGE_URL=$(echo $UPLOAD | jq -r .image_url)

# 3. Generate listing from uploaded image
curl -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"image_url\":\"$IMAGE_URL\",
    \"user_id\":\"$USER_ID\"
  }"

# See response with AI-generated title, description, price suggestion, etc.
```

For complete command reference, see **[COMMANDS.md](./COMMANDS.md)**

---

## Project Structure

```
scalency-backend/
├── app/
│   ├── api/
│   │   ├── health.py          # GET /health
│   │   ├── listings.py        # Listing endpoints
│   │   └── pricing.py         # Price suggestion endpoint
│   ├── core/
│   │   ├── config.py          # Pydantic-settings configuration
│   │   └── database.py        # SQLAlchemy engine + session
│   ├── models/
│   │   ├── user.py            # User ORM model
│   │   ├── listing.py         # Listing ORM model
│   │   └── job.py             # AutomationJob ORM model
│   ├── schemas/
│   │   └── listing_schema.py  # Pydantic v2 schemas
│   ├── services/
│   │   ├── ai_service.py      # OpenRouter integration
│   │   └── pricing_service.py # Rule-based price engine
│   ├── tasks/
│   │   ├── celery_worker.py   # Celery app factory
│   │   ├── publish_task.py    # Publish background task
│   │   └── repost_task.py     # Repost background task
│   └── main.py                # FastAPI app entrypoint
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── README.md
└── DEPLOYMENT.md
```

---

## Local Setup (without Docker)

**Prerequisites:** Python 3.11+, PostgreSQL, Redis running locally.

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd scalency-backend

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set DATABASE_URL, REDIS_URL, OPENROUTER_API_KEY

# 5. Start the API
uvicorn app.main:app --reload --port 8000

# 6. Start the Celery worker (separate terminal, venv activated)
celery -A app.tasks.celery_worker.celery_app worker --loglevel=info
```

---

## Docker Setup (recommended)

```bash
# 1. Copy and configure environment
cp .env.example .env
# Set OPENROUTER_API_KEY in .env

# 2. Build and start all services
docker-compose up --build

# To run in the background:
docker-compose up --build -d
```

All four services start automatically:

| Service | Port | Description |
|---|---|---|
| `api` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Redis broker |
| `worker` | — | Celery background worker |

Interactive API docs: http://localhost:8000/docs

---

## API Endpoint Overview

### Full API Documentation

For **complete endpoint documentation** with request/response examples, error codes, and use cases, see **[API_GUIDE.md](./API_GUIDE.md)**

Quick reference:

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service + DB health check |

### Listings

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/listings/generate` | Generate listing from image URL |
| `POST` | `/api/v1/listings` | Create a new listing |
| `POST` | `/api/v1/listings/{id}/publish` | Publish listing (background job) |
| `POST` | `/api/v1/listings/{id}/repost` | Repost listing (clone + republish) |
| `PATCH` | `/api/v1/listings/{id}/stock` | Update stock after a sale |

### Pricing

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/pricing/suggest` | Get price suggestion |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL DSN |
| `REDIS_URL` | Yes | — | Redis DSN |
| `OPENROUTER_API_KEY` | No* | — | OpenRouter API key (priority AI service) |
| `CLAUDE_API_KEY` | No* | — | Claude API key (fallback if OpenRouter unavailable) |
| `SECRET_KEY` | Yes | — | App secret (JWT signing etc.) |
| `OPENROUTER_MODEL` | No | `openai/gpt-4o-mini` | AI model for OpenRouter |
| `CLAUDE_MODEL` | No | `claude-3-5-sonnet-20241022` | Claude model to use |
| `DEBUG` | No | `false` | Enable debug logging |

**Note:** At least one AI service (OpenRouter OR Claude) must be configured. If OpenRouter fails, the system automatically falls back to Claude.

---

## 🛠️ Common Commands

For comprehensive command reference, see **[COMMANDS.md](./COMMANDS.md)**

Quick commands:

```bash
# View all services status
docker compose ps

# Follow API logs
docker compose logs -f scalency_api

# Connect to database
docker compose exec scalency_postgres psql -U scalency -d scalency

# Open Redis CLI
docker compose exec scalency_redis redis-cli

# Restart all services
docker compose restart

# View worker tasks
docker compose exec scalency_worker celery -A app.tasks.celery_worker inspect active
```

---

## Running Tests

```bash
pytest tests/ -v
```

*(Test suite can be added under a `tests/` directory following pytest conventions.)*

---

## 📖 Complete Documentation

This repository includes comprehensive documentation:

| Document | Contents |
|----------|----------|
| **[API_GUIDE.md](./API_GUIDE.md)** | ✅ Complete API reference with all endpoints, request/response formats, error codes, and examples |
| **[COMMANDS.md](./COMMANDS.md)** | ✅ Comprehensive command reference for Docker, Database, Celery, development, and troubleshooting |
| **[README.md](./README.md)** | ✅ Setup, architecture, quick start (you are here) |
| **[DEPLOYMENT.md](./DEPLOYMENT.md)** | ✅ Production deployment guides for DigitalOcean, AWS, and other platforms |

### Where to Go

- 🚀 **Starting now?** → Run Quick Start (above), then check [API_GUIDE.md](./API_GUIDE.md)
- 🔌 **Building an integration?** → Read [API_GUIDE.md](./API_GUIDE.md) for endpoint reference
- 🛠️ **Need a command?** → Search [COMMANDS.md](./COMMANDS.md)
- 🌍 **Ready for production?** → Follow [DEPLOYMENT.md](./DEPLOYMENT.md)
- 🐛 **Debugging an issue?** → See [COMMANDS.md](./COMMANDS.md#-troubleshooting-commands)
- 💻 **Local development?** → See [COMMANDS.md](./COMMANDS.md#-development-commands)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Follow the code style (Black formatting)
4. Run tests: `pytest tests/`
5. Commit: `git commit -m 'Add amazing feature'`
6. Push: `git push origin feature/amazing-feature`
7. Open a Pull Request

---

## 📞 Support & Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| API not responding | Check logs: `docker compose logs -f scalency_api` |
| Database connection error | Restart: `docker compose restart scalency_postgres` |
| AI service timeout | Verify OpenRouter key: `grep OPENROUTER_API_KEY .env` |
| Tasks not processing | Check worker: `docker compose logs -f scalency_worker` |

For more troubleshooting, see [COMMANDS.md#-troubleshooting-commands](./COMMANDS.md#-troubleshooting-commands)

### Getting Help

- 📖 Check the relevant guide ([API_GUIDE.md](./API_GUIDE.md), [COMMANDS.md](./COMMANDS.md), etc.)
- 🔍 Search existing issues on GitHub
- 📝 Create an issue with detailed error logs and steps to reproduce

---

## ✨ Quick Stats

- **Lines of Code:** ~2,500+ (app logic)
- **API Endpoints:** 10+ production-ready endpoints
- **Pricing Rules:** 25+ brand multipliers, 5 condition tiers
- **AI Models:** Support for 100+ models via OpenRouter
- **Task Queue:** Asynchronous with Celery + Redis
- **Database:** PostgreSQL with ORM (SQLAlchemy)
- **Documentation:** 1000+ lines across 4 guides

---

**Built with ❤️ for the Scalency marketplace**
#   S c a l e n c y - b a c k e n d 
 

 
