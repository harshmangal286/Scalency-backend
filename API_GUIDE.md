# Scalency Backend - API Access Guide

Complete documentation for all REST API endpoints available in the Scalency backend.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. However, most endpoints require a `user_id` to associate operations with a user account.

---

## 🔑 Users Endpoints

### Register New User

**Endpoint:** `POST /users`

Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response: 201 Created**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-03-13T10:30:45.123456+00:00"
}
```

**Errors:**
- `409 Conflict` - Email already registered
- `422 Unprocessable Entity` - Invalid email format or password too short (min 8 chars)

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "testpass123"
  }'
```

---

### Get User Details

**Endpoint:** `GET /users/{user_id}`

Retrieve user profile information.

**Parameters:**
- `user_id` (path, UUID) - User identifier

**Response: 200 OK**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "created_at": "2026-03-13T10:30:45.123456+00:00"
}
```

**Errors:**
- `404 Not Found` - User does not exist

**Example:**
```bash
curl http://localhost:8000/api/v1/users/550e8400-e29b-41d4-a716-446655440000
```

---

## 📋 Listings Endpoints

### Upload Image File

**Endpoint:** `POST /listings/upload`

Upload an image file and get a URL to use with the generate endpoint.

**Key Features:**
- Accept JPG, PNG, GIF, WebP formats
- Validate file size (max 10MB)
- Store file on server
- Return permanent URL for use with /listings/generate

**Request:**
```
Content-Type: multipart/form-data

file: <image file>
```

**Response: 200 OK**
```json
{
  "image_url": "http://localhost:8000/api/v1/listings/uploads/550e8400-e29b-41d4-a716-xxxxxxxxxxxxx.jpg",
  "filename": "550e8400-e29b-41d4-a716-xxxxxxxxxxxxx.jpg",
  "size": 245830
}
```

**Errors:**
- `422 Unprocessable Entity` - Invalid file type or exceeds 10MB
- `500 Internal Server Error` - Server file storage failed

**Example (cURL):**
```bash
curl -X POST http://localhost:8000/api/v1/listings/upload \
  -F "file=@/path/to/image.jpg"
```

**Example (JavaScript):**
```javascript
const formData = new FormData();
formData.append('file', fileInputElement.files[0]);

const response = await fetch('http://localhost:8000/api/v1/listings/upload', {
  method: 'POST',
  body: formData
});

const { image_url } = await response.json();

// Now use image_url with /listings/generate
const listing = await fetch('http://localhost:8000/api/v1/listings/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    image_url: image_url,
    user_id: userId
  })
});
```

---

### Generate AI Listing from Image

**Endpoint:** `POST /listings/generate`

Automatically extract product attributes from an image URL using AI.

**Key Features:**
- AI-powered attribute extraction (OpenRouter → Claude fallback)
- Auto-computes price suggestion
- Creates draft listing in database
- Returns listing_id for immediate use

**AI Service Priority:**
1. OpenRouter (if `OPENROUTER_API_KEY` configured)
2. Claude API (if `CLAUDE_API_KEY` configured)
3. Error if neither available

**Request:**
```json
{
  "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response: 201 Created**
```json
{
  "listing_id": "a1b2c3d4-e5f6-41d4-a716-xxxxxxxxxxxxx",
  "title": "Levi's Black Graphic Tee with Red Trim",
  "description": "Elevate your casual wardrobe with this stylish Levi's black graphic tee featuring a bold red trim...",
  "brand": "Levi's",
  "category": "shirt",
  "material": "cotton",
  "style": "casual",
  "color": "black",
  "condition_estimate": "new",
  "hashtags": ["#Levis", "#GraphicTee", "#CasualStyle"],
  "image_urls": ["https://images.unsplash.com/..."],
  "price_suggestion": {
    "recommended_price": 45.00,
    "min_price": 36.00,
    "max_price": 54.00
  }
}
```

**Errors:**
- `422 Unprocessable Entity` - Invalid image URL or missing fields
- `404 Not Found` - User does not exist
- `502 Bad Gateway` - AI service unavailable

**Timing:** 5-15 seconds (calls external AI service)

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400",
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

### Create Listing

**Endpoint:** `POST /listings`

Create a new listing (manually or from generated attributes).

**Request:**
```json
{
  "title": "Levi's Black Graphic Tee",
  "description": "High-quality cotton t-shirt",
  "brand": "Levi's",
  "category": "shirt",
  "material": "cotton",
  "style": "casual",
  "color": "black",
  "condition_estimate": "new",
  "hashtags": ["#Levis", "#Fashion"],
  "image_urls": ["https://images.example.com/image.jpg"],
  "price": 45.00,
  "stock": 5,
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response: 201 Created**
```json
{
  "id": "listing-uuid-here",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Levi's Black Graphic Tee",
  "description": "High-quality cotton t-shirt",
  "brand": "Levi's",
  "category": "shirt",
  "status": "DRAFT",
  "price": 45.00,
  "stock": 5,
  "created_at": "2026-03-13T10:30:45.123456+00:00"
}
```

**Notes:**
- If `price` is not provided, it's auto-calculated if all required fields present
- Status defaults to `DRAFT`
- Returns listing ID for publishing

**Errors:**
- `404 Not Found` - User does not exist
- `422 Unprocessable Entity` - Missing required fields

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/listings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Levi\''s Black Graphic Tee",
    "description": "High-quality cotton t-shirt",
    "brand": "Levi\''s",
    "category": "shirt",
    "material": "cotton",
    "style": "casual",
    "color": "black",
    "hashtags": ["#Levis"],
    "image_urls": ["https://example.com/image.jpg"],
    "stock": 5,
    "user_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

---

### List All Listings

**Endpoint:** `GET /listings`

Retrieve all listings with pagination support.

**Query Parameters:**
- `limit` (int, default: 100) - Number of listings per page
- `offset` (int, default: 0) - Pagination offset

**Response: 200 OK**
```json
{
  "items": [
    {
      "id": "listing-id-1",
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Levi's Black Graphic Tee",
      "status": "PUBLISHED",
      "price": 45.00,
      "created_at": "2026-03-13T10:30:45.123456+00:00"
    },
    {
      "id": "listing-id-2",
      "user_id": "550e8400-e29b-41d4-a716-446655440001",
      "title": "USPA Polo Shirt",
      "status": "DRAFT",
      "price": 35.00,
      "created_at": "2026-03-13T11:15:30.654321+00:00"
    }
  ],
  "total": 2
}
```

**Example:**
```bash
# Get first 10 listings
curl "http://localhost:8000/api/v1/listings?limit=10&offset=0"

# Get next 10 listings
curl "http://localhost:8000/api/v1/listings?limit=10&offset=10"
```

---

### Get Listing Details

**Endpoint:** `GET /listings/{listing_id}`

Retrieve detailed information about a specific listing.

**Parameters:**
- `listing_id` (path, UUID) - Listing identifier

**Response: 200 OK**
```json
{
  "id": "listing-id",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Levi's Black Graphic Tee",
  "description": "High-quality cotton t-shirt",
  "brand": "Levi's",
  "category": "shirt",
  "material": "cotton",
  "style": "casual",
  "color": "black",
  "condition_estimate": "new",
  "status": "PUBLISHED",
  "price": 45.00,
  "stock": 5,
  "image_urls": ["https://example.com/image.jpg"],
  "created_at": "2026-03-13T10:30:45.123456+00:00",
  "updated_at": "2026-03-13T10:35:00.000000+00:00"
}
```

**Errors:**
- `404 Not Found` - Listing does not exist

**Example:**
```bash
curl http://localhost:8000/api/v1/listings/listing-id-here
```

---

### Update Listing

**Endpoint:** `PATCH /listings/{listing_id}`

Update listing details.

**Parameters:**
- `listing_id` (path, UUID) - Listing identifier

**Request (all fields optional):**
```json
{
  "title": "Updated Title",
  "price": 50.00,
  "stock": 10,
  "description": "Updated description",
  "status": "ARCHIVED"
}
```

**Response: 200 OK**
```json
{
  "id": "listing-id",
  "title": "Updated Title",
  "price": 50.00,
  "stock": 10,
  "updated_at": "2026-03-13T10:35:00.000000+00:00"
}
```

**Errors:**
- `404 Not Found` - Listing does not exist

**Example:**
```bash
curl -X PATCH http://localhost:8000/api/v1/listings/listing-id-here \
  -H "Content-Type: application/json" \
  -d '{
    "price": 50.00,
    "stock": 10
  }'
```

---

### Publish Listing

**Endpoint:** `POST /listings/{listing_id}/publish`

Publish a listing and trigger background job processing.

**Parameters:**
- `listing_id` (path, UUID) - Listing identifier

**Response: 202 Accepted** (Async operation)
```json
{
  "job_id": "c053fd73-4276-41b9-b63b-a7012d45a2e2",
  "status": "queued"
}
```

**Workflow:**
1. Listing status changes to `PROCESSING`
2. Celery background job queued
3. Job ID returned immediately for polling
4. Use this job_id with `/jobs/{job_id}` to track completion

**Errors:**
- `404 Not Found` - Listing does not exist
- `400 Bad Request` - Listing already published or cannot be published

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/listings/listing-id-here/publish
```

---

## 🔄 Jobs Endpoints

### Poll Job Status

**Endpoint:** `GET /jobs/{job_id}`

Check the status of a background job (publish, repost, etc.).

**Parameters:**
- `job_id` (path, UUID) - Job identifier (from publish response)

**Response: 200 OK**
```json
{
  "id": "c053fd73-4276-41b9-b63b-a7012d45a2e2",
  "task_name": "publish_listing_task",
  "status": "pending",
  "created_at": "2026-03-13T10:40:00.000000+00:00"
}
```

**Job Status Values:**
- `pending` - Job in queue or processing
- `success` - Job completed successfully
- `failed` - Job failed

**Response on Completion (Success):**
```json
{
  "id": "c053fd73-4276-41b9-b63b-a7012d45a2e2",
  "task_name": "publish_listing_task",
  "status": "success",
  "result": {
    "listing_id": "listing-id",
    "status": "PUBLISHED",
    "message": "Listing published successfully"
  },
  "completed_at": "2026-03-13T10:41:30.000000+00:00"
}
```

**Response on Failure:**
```json
{
  "id": "c053fd73-4276-41b9-b63b-a7012d45a2e2",
  "task_name": "publish_listing_task",
  "status": "failed",
  "error_message": "Error details here",
  "completed_at": "2026-03-13T10:41:45.000000+00:00"
}
```

**Frontend Polling Pattern:**
```javascript
// Poll every 2 seconds until completion
const pollInterval = setInterval(async () => {
  const response = await fetch(`/api/v1/jobs/${jobId}`);
  const job = await response.json();

  if (job.status === 'success' || job.status === 'failed') {
    clearInterval(pollInterval);
    // Handle completion
  }
}, 2000);
```

**Errors:**
- `404 Not Found` - Job does not exist

**Example:**
```bash
curl http://localhost:8000/api/v1/jobs/c053fd73-4276-41b9-b63b-a7012d45a2e2
```

---

## 💰 Pricing Endpoints

### Get Price Suggestion

**Endpoint:** `POST /pricing/suggest`

Calculate recommended price for a product.

**Request:**
```json
{
  "brand": "Levi's",
  "category": "shirt",
  "condition": "new"
}
```

**Response: 200 OK**
```json
{
  "recommended_price": 45.00,
  "min_price": 36.00,
  "max_price": 54.00
}
```

**Pricing Logic:**
- Base price determined by category
- Multiplied by brand reputation factor
- Multiplied by condition factor
- ±20% spread applied

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/pricing/suggest \
  -H "Content-Type: application/json" \
  -d '{
    "brand": "Levi\''s",
    "category": "shirt",
    "condition": "new"
  }'
```

---

## 🏥 Health Check

### System Health

**Endpoint:** `GET /health`

Check if the API is running.

**Response: 200 OK**
```json
{
  "status": "ok"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

## 📊 Common Workflows

### Complete Flow: Image to Published Listing

```bash
# 1. Register user
USER_ID=$(curl -s -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}' \
  | jq -r .id)

# 2. Generate listing from image
LISTING=$(curl -s -X POST http://localhost:8000/api/v1/listings/generate \
  -H "Content-Type: application/json" \
  -d "{\"image_url\":\"https://example.com/image.jpg\",\"user_id\":\"$USER_ID\"}")
LISTING_ID=$(echo $LISTING | jq -r .listing_id)

# 3. Create/save the generated listing
curl -s -X POST http://localhost:8000/api/v1/listings \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"$(echo $LISTING | jq -r .title)\",\"description\":\"$(echo $LISTING | jq -r .description)\",\"user_id\":\"$USER_ID\",\"brand\":\"$(echo $LISTING | jq -r .brand)\",\"category\":\"$(echo $LISTING | jq -r .category)\",\"material\":\"$(echo $LISTING | jq -r .material)\",\"style\":\"$(echo $LISTING | jq -r .style)\",\"color\":\"$(echo $LISTING | jq -r .color)\",\"stock\":1}"

# 4. Publish listing
JOB=$(curl -s -X POST http://localhost:8000/api/v1/listings/$LISTING_ID/publish)
JOB_ID=$(echo $JOB | jq -r .job_id)

# 5. Poll job status
while true; do
  STATUS=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq -r .status)
  echo "Job status: $STATUS"

  if [ "$STATUS" == "success" ] || [ "$STATUS" == "failed" ]; then
    break
  fi

  sleep 2
done
```

---

## 🔗 Interactive API Documentation

Visit these URLs for interactive API testing:

- **Swagger UI** (Interactive): http://localhost:8000/docs
- **ReDoc** (Beautiful Docs): http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 📝 Request/Response Format

### All responses include:
```json
{
  "data": {...},           // Actual response data
  "timestamp": "...",      // ISO 8601 timestamp
  "status": 200            // HTTP status code
}
```

### Error responses:
```json
{
  "detail": "Error message",
  "status": 400
}
```

---

## ⚠️ Rate Limiting

Currently not implemented but recommended for production. See deployment guides for setup.

---

## 🔐 CORS & Security

- CORS enabled for frontend at `http://localhost:3000` and `http://localhost:5173`
- No authentication currently required (add JWT in production)
- All inputs validated with Pydantic

---

## 📞 API Status Codes

| Code | Meaning |
|------|---------|
| 200 | ✅ OK - Request successful |
| 201 | ✅ Created - Resource created |
| 202 | ✅ Accepted - Async job accepted |
| 400 | ❌ Bad Request - Invalid input |
| 404 | ❌ Not Found - Resource doesn't exist |
| 409 | ❌ Conflict - Resource already exists |
| 422 | ❌ Unprocessable Entity - Validation error |
| 500 | ❌ Server Error |
| 502 | ❌ Bad Gateway - External service unavailable |

---

For more information, see [README.md](./README.md) or [COMMANDS.md](./COMMANDS.md).
