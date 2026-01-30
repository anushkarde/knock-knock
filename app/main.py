"""FastAPI app and routes for Knock Knock."""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import ANGI_API_KEY
from app.db import init_db, get_db, SessionLocal
from app.schemas import AngiLeadWebhookPayload
from app.services import process_angi_lead
from app.seed import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed demo data on startup."""
    init_db()
    db = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
    yield
    # shutdown: nothing to do


app = FastAPI(
    title="Knock Knock",
    description="Ingest Angi leads via webhook, map to tenant, send outreach email.",
    version="0.1.0",
    lifespan=lifespan,
)


def verify_angi_api_key(x_api_key: str | None = Header(None, alias="X-API-KEY")) -> None:
    """Require X-API-KEY header to match ANGI_API_KEY."""
    if not ANGI_API_KEY or x_api_key != ANGI_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/healthz")
def healthz():
    """Health check."""
    return {"ok": True}


@app.post(
    "/webhooks/angi/leads",
    response_class=PlainTextResponse,
    status_code=200,
)
async def webhook_angi_leads(
    request: Request,
    _: None = Depends(verify_angi_api_key),
    db: Session = Depends(get_db),
):
    """
    Ingest Angi lead webhook: verify key, parse payload, dedupe by correlation_id,
    map tenant, persist lead, send email, return success.
    """
    body_bytes = await request.body()
    raw_json = body_bytes.decode("utf-8") if body_bytes else ""

    try:
        payload_dict = json.loads(raw_json) if raw_json else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    payload = AngiLeadWebhookPayload.model_validate(payload_dict)

    is_duplicate, err_msg = process_angi_lead(db, payload, raw_json)

    if is_duplicate:
        return PlainTextResponse("<success>ok</success>", status_code=200)
    if err_msg:
        # Still return 200 per spec; log the failure
        return PlainTextResponse("<success>ok</success>", status_code=200)
    return PlainTextResponse("<success>ok</success>", status_code=200)
