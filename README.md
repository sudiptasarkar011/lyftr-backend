# Lyftr AI - Backend Assignment

A containerized Webhook API built with FastAPI, SQLite, and Docker.

## Features
- **Ingestion**: Accepts WhatsApp-like messages via `/webhook` with HMAC validation.
- **Idempotency**: Prevents duplicate processing using `message_id`.
- **Querying**: Filtering and pagination via `/messages`.
- **Observability**: Prometheus metrics at `/metrics` and structured JSON logs.

## Setup & Running

### Prerequisites
- Docker & Docker Compose
- Make (optional, but recommended)

### Quick Start
1. **Start the service**:
   ```bash
   make up
   # OR: docker compose up -d --build