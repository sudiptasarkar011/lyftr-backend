import hmac
import hashlib
import time
import uuid
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Header, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.storage import init_db, get_db, MessageDB
from app.models import WebhookPayload
from app.logging_utils import logger

HTTP_REQUESTS_TOTAL = Counter("http_requests_total", "Total HTTP requests", ["path", "status"])
WEBHOOK_REQUESTS_TOTAL = Counter("webhook_requests_total", "Webhook processing outcomes", ["result"])
REQUEST_LATENCY = Histogram("request_latency_ms", "Request latency in ms")

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET is not set")
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    path = request.url.path
    status_code = str(response.status_code)
    HTTP_REQUESTS_TOTAL.labels(path=path, status=status_code).inc()
    REQUEST_LATENCY.observe(process_time)

    log_data = {
        "request_id": request_id,
        "method": request.method,
        "path": path,
        "status": status_code,
        "latency_ms": round(process_time, 2)
    }
    
    if hasattr(request.state, "webhook_log"):
        log_data.update(request.state.webhook_log)

    logger.info("Request processed", extra=log_data)
    
    return response

async def verify_signature(request: Request):
    signature = request.headers.get("X-Signature")
    if not signature:
        WEBHOOK_REQUESTS_TOTAL.labels(result="invalid_signature").inc()
        logger.error("Missing signature", extra={"result": "invalid_signature"})
        raise HTTPException(status_code=401, detail="invalid signature")

    body_bytes = await request.body()
    
    computed_hmac = hmac.new(
        key=settings.webhook_secret.encode(),
        msg=body_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hmac, signature):
        WEBHOOK_REQUESTS_TOTAL.labels(result="invalid_signature").inc()
        logger.error("Invalid signature", extra={"result": "invalid_signature"})
        raise HTTPException(status_code=401, detail="invalid signature")
    
    return body_bytes

@app.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body_bytes = await verify_signature(request)
    
    try:
        payload = WebhookPayload.model_validate_json(body_bytes)
    except Exception as e:
        WEBHOOK_REQUESTS_TOTAL.labels(result="validation_error").inc()
        raise HTTPException(status_code=422, detail=str(e))

    request.state.webhook_log = {"message_id": payload.message_id, "dup": False}

    query = select(MessageDB).where(MessageDB.message_id == payload.message_id)
    result = await db.execute(query)
    existing_message = result.scalar_one_or_none()

    if existing_message:
        request.state.webhook_log["dup"] = True
        request.state.webhook_log["result"] = "duplicate"
        WEBHOOK_REQUESTS_TOTAL.labels(result="duplicate").inc()
        return {"status": "ok"}

    new_msg = MessageDB(
        message_id=payload.message_id,
        from_msisdn=payload.from_match,
        to_msisdn=payload.to,
        ts=payload.ts,
        text=payload.text
    )
    db.add(new_msg)
    await db.commit()
    
    request.state.webhook_log["result"] = "created"
    WEBHOOK_REQUESTS_TOTAL.labels(result="created").inc()
    
    return {"status": "ok"}

@app.get("/messages")
async def list_messages(
    limit: int = 50,
    offset: int = 0,
    from_msisdn: Optional[str] = None,
    since: Optional[datetime] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(MessageDB)
    
    if from_msisdn:
        query = query.where(MessageDB.from_msisdn == from_msisdn)
    if since:
        query = query.where(MessageDB.ts >= since)
    if q:
        query = query.where(MessageDB.text.ilike(f"%{q}%"))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(asc(MessageDB.ts), asc(MessageDB.message_id))
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    messages = result.scalars().all()

    data = []
    for m in messages:
        data.append({
            "message_id": m.message_id,
            "from": m.from_msisdn,
            "to": m.to_msisdn,
            "ts": m.ts.isoformat().replace("+00:00", "Z"),
            "text": m.text
        })

    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count(MessageDB.message_id)))
    senders = await db.scalar(select(func.count(func.distinct(MessageDB.from_msisdn))))
    
    top_senders_q = select(MessageDB.from_msisdn, func.count(MessageDB.message_id).label("count"))\
        .group_by(MessageDB.from_msisdn)\
        .order_by(desc("count"))\
        .limit(10)
    
    top_senders_res = await db.execute(top_senders_q)
    messages_per_sender = [{"from": row[0], "count": row[1]} for row in top_senders_res]

    min_ts = await db.scalar(select(func.min(MessageDB.ts)))
    max_ts = await db.scalar(select(func.max(MessageDB.ts)))

    return {
        "total_messages": total or 0,
        "senders_count": senders or 0,
        "messages_per_sender": messages_per_sender,
        "first_message_ts": min_ts.isoformat().replace("+00:00", "Z") if min_ts else None,
        "last_message_ts": max_ts.isoformat().replace("+00:00", "Z") if max_ts else None
    }

@app.get("/health/live")
def health_live():
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready(db: AsyncSession = Depends(get_db)):
    try:
        # Check DB connection
        await db.execute(select(1))
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)