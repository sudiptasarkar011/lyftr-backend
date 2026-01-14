# Lyftr Backend - Webhook API

A production-ready webhook API built with FastAPI, SQLAlchemy, and SQLite. Accepts and processes WhatsApp-like messages with HMAC authentication, idempotency guarantees, and full observability.

## Features

- **Secure Webhook Ingestion**: HMAC-SHA256 signature verification
- **Idempotent Processing**: Duplicate message prevention using `message_id`
- **Data Validation**: E.164 phone number format validation with Pydantic
- **Message Querying**: Advanced filtering, pagination, and full-text search
- **Statistics API**: Message analytics with sender metrics
- **Observability**: Prometheus metrics and structured JSON logging
- **Health Checks**: Liveness and readiness endpoints
- **Async Architecture**: Built on SQLAlchemy async with aiosqlite

## Prerequisites

- Python 3.10+ (for local development)
- Docker & Docker Compose (for containerized deployment)
- Make (optional, recommended)

## Installation & Setup

### Option 1: Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd lyftr-backend
   ```

2. **Configure environment**:
   ```bash
   cp .env .env.local
   # Edit .env and set WEBHOOK_SECRET
   ```

3. **Build and run**:
   ```bash
   docker compose build
   docker compose up -d
   ```

4. **Check status**:
   ```bash
   curl http://localhost:8000/health/live
   ```

### Option 2: Local Development

1. **Create virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   # Create .env file with:
   WEBHOOK_SECRET=your_secret_here
   DATABASE_URL=sqlite+aiosqlite:///./data/app.db
   LOG_LEVEL=INFO
   ```

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Webhook Ingestion

**POST /webhook**

Accepts incoming messages with HMAC signature validation.

```bash
# Generate signature
SECRET="your_webhook_secret_here"
PAYLOAD='{"message_id": "m1", "from":"+919876543210", "to":"+14155550100", "ts":"2025-01-15T10:00:00Z", "text": "Hello"}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$PAYLOAD"
```

**Request Body**:
```json
{
  "message_id": "unique_id",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Optional message text"
}
```

**Response**: `200 OK`
```json
{"status": "ok"}
```

### Query Messages

**GET /messages**

Retrieve messages with filtering and pagination.

```bash
# Basic query
curl "http://localhost:8000/messages?limit=10&offset=0"

# With filters
curl "http://localhost:8000/messages?from_msisdn=%2B919876543210&since=2025-01-01T00:00:00Z&q=hello"
```

**Query Parameters**:
- `limit` (int): Results per page (default: 50)
- `offset` (int): Pagination offset (default: 0)
- `from_msisdn` (string): Filter by sender phone number
- `since` (datetime): Filter messages after this timestamp
- `q` (string): Full-text search in message text

**Response**: `200 OK`
```json
{
  "data": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Statistics

**GET /stats**

Get message statistics and analytics.

```bash
curl http://localhost:8000/stats
```

**Response**: `200 OK`
```json
{
  "total_messages": 100,
  "senders_count": 25,
  "messages_per_sender": [
    {"from": "+919876543210", "count": 15},
    {"from": "+14155550100", "count": 12}
  ],
  "first_message_ts": "2025-01-01T00:00:00Z",
  "last_message_ts": "2025-01-15T10:00:00Z"
}
```

### Health Checks

**GET /health/live**

Liveness probe - always returns 200 if service is running.

**GET /health/ready**

Readiness probe - checks database connectivity.

### Metrics

**GET /metrics**

Prometheus-compatible metrics endpoint.

**Available Metrics**:
- `http_requests_total`: Total HTTP requests by path and status
- `webhook_requests_total`: Webhook processing outcomes (created/duplicate/invalid_signature)
- `request_latency_ms`: Request processing latency histogram

## Testing

### Run Tests with Docker

```bash
docker compose run --rm api pytest
```

### Run Tests Locally

```bash
pytest tests/ -v
```

### Test Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

## Project Structure

```
lyftr-backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application and endpoints
│   ├── config.py         # Settings and configuration
│   ├── models.py         # Pydantic models
│   ├── storage.py        # Database models and session
│   └── logging_utils.py  # Structured logging setup
├── tests/
│   ├── __init__.py
│   ├── conftest.py       # Pytest fixtures
│   └── test_webhook.py   # Webhook endpoint tests
├── data/                 # SQLite database storage
├── docker-compose.yml    # Docker compose configuration
├── Dockerfile            # Container image definition
├── requirements.txt      # Python dependencies
├── pytest.ini            # Pytest configuration
├── Makefile              # Development shortcuts
└── README.md
```

## Development

### Makefile Commands

```bash
make up      # Start services
make down    # Stop services
make logs    # View logs
make test    # Run tests (requires Docker)
```

### Database Migrations

The database schema is automatically created on startup. For production, consider using Alembic for migrations.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_SECRET` | HMAC secret key for signature validation | Required |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./data/app.db` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `APP_NAME` | Application name | `Lyftr Webhook API` |

## Security Considerations

- **HMAC Authentication**: All webhook requests must include valid `X-Signature` header
- **Input Validation**: Phone numbers validated against E.164 format
- **SQL Injection**: Protected by SQLAlchemy ORM
- **Idempotency**: Duplicate messages rejected based on `message_id`

## Performance

- **Async I/O**: Non-blocking database operations with SQLAlchemy async
- **Connection Pooling**: Managed by SQLAlchemy engine
- **Efficient Queries**: Indexed lookups on `message_id` and `from_msisdn`

## Troubleshooting

### Issue: "Invalid signature" error

Ensure the signature is computed correctly:
```python
import hmac
import hashlib

payload = b'{"message_id": "m1", ...}'
secret = b"your_webhook_secret_here"
signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
```

### Issue: Python 3.13 compatibility

If using Python 3.13, ensure SQLAlchemy >= 2.0.36 and greenlet are installed:
```bash
pip install --upgrade 'sqlalchemy>=2.0.36' greenlet
```

### Issue: Docker not found

Install Docker Desktop from https://www.docker.com/products/docker-desktop/

## Setup Used

VSCode + Copilot + occasional Gemini prompts
