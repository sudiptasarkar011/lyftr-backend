import pytest
import hmac
import hashlib
import json
from app.config import settings

SECRET = settings.webhook_secret

def generate_signature(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

@pytest.mark.asyncio
async def test_webhook_valid_signature(client):
    payload = {
        "message_id": "test_m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello World"
    }
    body = json.dumps(payload).encode()
    signature = generate_signature(SECRET, body)
    
    response = await client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    payload = {"message_id": "m2", "from": "+123", "to": "+456", "ts": "2025-01-01T00:00:00Z"}
    body = json.dumps(payload).encode()
    
    response = await client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": "invalid_hex", "Content-Type": "application/json"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "invalid signature"

@pytest.mark.asyncio
async def test_webhook_idempotency(client):
    payload = {
        "message_id": "unique_id_1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Idempotency Test"
    }
    body = json.dumps(payload).encode()
    signature = generate_signature(SECRET, body)
    
    # First call
    resp1 = await client.post("/webhook", content=body, headers={"X-Signature": signature})
    assert resp1.status_code == 200
    
    # Second call (same ID)
    resp2 = await client.post("/webhook", content=body, headers={"X-Signature": signature})
    assert resp2.status_code == 200
    
    # Verify only 1 message in DB
    stats = await client.get("/stats")
    assert stats.json()["total_messages"] == 1