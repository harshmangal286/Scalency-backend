# 🚀 Scalency Backend

### The Intelligence Layer for Modern Resale Marketplaces

Scalency is a high-performance, AI-assisted resale marketplace engine. It leverages **FastAPI**, **PostgreSQL**, and **Celery** to automate the heavy lifting of e-commerce—from image-to-listing generation to intelligent dynamic pricing and automated inventory management.

---

## 🧭 Documentation Hub

| Guide | Purpose |
| --- | --- |
| 📖 **[API_GUIDE.md](https://www.google.com/search?q=./API_GUIDE.md)** | Complete endpoint documentation with request/response examples. |
| 🛠️ **[COMMANDS.md](https://www.google.com/search?q=./COMMANDS.md)** | Essential CLI reference for Docker, Database, and Celery. |
| 🏠 **[README.md](https://www.google.com/search?q=./README.md)** | You are here: Architecture, Setup, and Overview. |
| 🚀 **[DEPLOYMENT.md](https://www.google.com/search?q=./DEPLOYMENT.md)** | Production-ready guides for Cloud hosting. |

---

## ✨ Core Capabilities

* **🤖 AI Listing Generation:** Transform a single image URL into a professional listing (Title, Description, Hashtags, Category).
* **⚖️ Smart Pricing Engine:** Rule-based suggestions derived from brand equity, category trends, and item condition.
* **⚙️ Background Automation:** Asynchronous publishing and task tracking via Celery & Redis.
* **🔄 Auto-Repost System:** Intelligent stock monitoring that clones and republishes listings until inventory is depleted.
* **📊 Job Tracking:** Real-time visibility into every background operation through the `AutomationJob` model.

---

## 🛠️ Technology Stack

* **Framework:** FastAPI (Asynchronous Python 3.11+)
* **Database:** PostgreSQL (SQLAlchemy 2.0 ORM)
* **Task Queue:** Celery + Redis
* **AI Intelligence:** OpenRouter (GPT-4o / Claude 3.5 Sonnet)
* **DevOps:** Docker & Docker Compose

---

## ⚡ Quick Start (Get running in < 2 mins)

### 1. Environment Setup

```bash
git clone <repo-url> && cd scalency-backend
cp .env.example .env
# Open .env and add your OPENROUTER_API_KEY

```

### 2. Launch Services

```bash
docker compose up -d --build

```

### 3. Verify & Explore

* **Health Check:** `curl http://localhost:8000/health`
* **Interactive Docs:** [http://localhost:8000/docs](https://www.google.com/search?q=http://localhost:8000/docs) (Swagger UI)

---

## 🧪 Testing the AI Flow

**Option: Generate Listing from Image**

```bash
# Create a user and capture ID
USER_ID=$(curl -s -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"dev@scalency.com","password":"secure-pass"}' | jq -r .id)
# Generate listing via AI
curl -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"image_url\":\"https://images.unsplash.com/photo-1505740420928-5e560c06d30e\",
    \"user_id\":\"$USER_ID\"
  }"

```

---

## 📂 Project Architecture

```text
scalency-backend/
├── app/
│   ├── api/            # Route handlers (Listings, Pricing, Users)
│   ├── core/           # Config, Security, Database sessions
│   ├── models/         # SQLAlchemy ORM definitions
│   ├── schemas/        # Pydantic v2 validation models
│   ├── services/       # Business logic & AI Integrations
│   ├── tasks/          # Celery worker & background jobs
│   └── main.py         # App entrypoint
├── tests/              # Pytest suite
└── docker-compose.yml  # Infrastructure orchestration

```

---

## 🔧 Infrastructure Management

| Task | Command |
| --- | --- |
| **View Logs** | `docker compose logs -f api` |
| **Reset DB** | `docker compose exec postgres dropdb -U scalency scalency` |
| **Worker Status** | `docker compose exec worker celery -A app.tasks.celery_worker status` |
| **Restart Stack** | `docker compose restart` |

---

## 📞 Support & Debugging

If you encounter issues, please check:

1. **AI Failures:** Ensure your `OPENROUTER_API_KEY` has active credits.
2. **Task Delays:** Verify Redis is healthy: `docker compose ps`.
3. **Logs:** Run `docker compose logs -f worker` to see background processing errors.
For deeper troubleshooting, refer to the **[Troubleshooting Section in COMMANDS.md](https://www.google.com/search?q=./COMMANDS.md%23-troubleshooting-commands)**.

**Built with ❤️ for the Scalency ecosystem.**

Would you like me to help you generate the content for the **API_GUIDE.md** or **COMMANDS.md** files mentioned here?
