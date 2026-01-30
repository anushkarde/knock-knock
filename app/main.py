"""FastAPI app and routes for Knock Knock."""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
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


async def verify_angi_api_key(
    request: Request,
    x_api_key: str | None = Header(None, alias="X-API-KEY"),
) -> None:
    """Require X-API-KEY header (or api_key query param) to match ANGI_API_KEY."""
    # Header first; fallback to query param (some proxies e.g. ngrok strip custom headers)
    key_from_header = (x_api_key.strip() if x_api_key else None) or None
    key_from_query = request.query_params.get("api_key")
    supplied_key = key_from_header or (key_from_query.strip() if key_from_query else None) or None
    if not ANGI_API_KEY or supplied_key != ANGI_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page for interviewers: instructions + copy-paste curl with correct base URL."""
    base = str(request.base_url).rstrip("/")
    curl_url = f"{base}/webhooks/angi/leads"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Knock Knock – Angi webhook</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.5rem; }}
    p {{ color: #444; line-height: 1.5; }}
    pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; border-radius: 6px; font-size: 0.85rem; }}
    code {{ font-family: ui-monospace, monospace; }}
    .note {{ background: #f0f7ff; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0; }}
    a {{ color: #0066cc; }}
  </style>
</head>
<body>
  <h1>Knock Knock – Angi lead webhook</h1>
  <p>To simulate an Angi API call, send a POST request to the webhook endpoint. Use the curl command below (replace <code>YOUR_API_KEY</code> with the API key provided by the host).</p>
  <div class="note"><strong>Run this in your terminal:</strong></div>
  <pre id="curl">curl -X POST {curl_url} \\
  -H "Content-Type: application/json" \\
  -H "X-API-KEY: YOUR_API_KEY" \\
  -d '{{
    "CorrelationId": "lead-001",
    "ALAccountId": "123456",
    "Email": "customer@example.com",
    "PhoneNumber": "+15551234567",
    "FirstName": "Jane",
    "LastName": "Doe",
    "Description": "Need plumbing repair",
    "Category": "Plumbing",
    "Urgency": "high",
    "PostalAddress": {{
      "AddressFirstLine": "123 Main St",
      "City": "Boston",
      "State": "MA",
      "PostalCode": "02101"
    }}
  }}'</pre>
  <p><button onclick="navigator.clipboard.writeText(document.getElementById('curl').innerText)">Copy curl</button></p>
  <p>Alternatively, put the key in the URL: <code>{base}/webhooks/angi/leads?api_key=YOUR_API_KEY</code> (same POST body).</p>
  <p><a href="/docs">Open API docs (Swagger)</a> · <a href="/healthz">Health check</a></p>
</body>
</html>"""
    return HTMLResponse(html)


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
