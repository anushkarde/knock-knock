# Knock Knock

A FastAPI service that ingests **Angi leads** via webhook, stores them, maps them to a tenant, and sends an outbound email on behalf of the tenant.

- **Database**: SQLite by default (`doorbell.db`), Postgres supported via `DATABASE_URL`.
- **Email**: SendGrid when `SENDGRID_API_KEY` is set; otherwise emails are printed to the console.
- **Optional**: OpenAI drafting when `USE_LLM_EMAIL=true` and `OPENAI_API_KEY` is set; falls back to a deterministic template if LLM is disabled or fails.

---

## Setup

1. **Create a virtual environment and install dependencies**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env and set ANGI_API_KEY (required for webhook auth).
   # Optionally set SENDGRID_API_KEY, OPENAI_API_KEY, USE_LLM_EMAIL, DATABASE_URL.
   ```

---

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000>
- Docs: <http://127.0.0.1:8000/docs>

---

## Exposing the webhook with ngrok

To receive Angi webhooks locally:

1. Install [ngrok](https://ngrok.com/download).
2. Run the app (see above), then in another terminal:

   ```bash
   ngrok http 8000
   ```

3. Use the HTTPS URL ngrok shows (e.g. `https://abc123.ngrok.io`) as your webhook URL, and append the path:  
   `https://abc123.ngrok.io/webhooks/angi/leads`.

---

## To test the webhook

1. You will receive an **ngrok link** (e.g. `https://abc123.ngrok-free.app`) from me.
2. **Open that link in your browser.** You’ll see a short instructions page and a **copy-paste curl** with the URL already filled in.
3. Replace `YOUR_API_KEY` in the curl with the API key the host gives you.
4. Run the curl in your terminal. You should get `200` and `<success>ok</success>`.

You can also use the same link + `/docs` for Swagger UI.

---

## Example curl (Angi lead webhook)

```bash
curl -X POST http://127.0.0.1:8000/webhooks/angi/leads \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: knock-knock-key" \
  -d '{
    "CorrelationId": "lead-001234567",
    "ALAccountId": "123456",
    "Email": "customer@example.com",
    "PhoneNumber": "+15551234567",
    "FirstName": "Jane",
    "LastName": "Doe",
    "Description": "Need plumbing repair",
    "Category": "Plumbing",
    "Urgency": "high",
    "PostalAddress": {
      "AddressFirstLine": "123 Main St",
      "City": "Boston",
      "State": "MA",
      "PostalCode": "02101"
    }
  }'
```

Replace `your-angi-webhook-api-key` with the value of `ANGI_API_KEY` in your `.env`.  
Expected response: `200` with body `<success>ok</success>`.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/healthz` | Health check. Returns `{"ok": true}`. |
| POST | `/webhooks/angi/leads` | Angi lead webhook. Requires header `X-API-KEY` = `ANGI_API_KEY`; returns `401` if missing or invalid. |

---

## Database

- **Default**: SQLite file `doorbell.db` in the project root (same directory as `uvicorn` is run from).
- **Postgres**: Set `DATABASE_URL=postgresql://user:pass@host:5432/dbname`.

Tables are created on startup via `init_db()` (no Alembic). To inspect tables, open the DB with the SQLite CLI: `sqlite3 doorbell.db`. Inside the prompt, use `.tables` to list tables, `.schema` (or `.schema <table>`) to show definitions, and run `SELECT * FROM <table>;` to view rows (use `.headers on` and `.mode column` for readable output).

```bash
sqlite3 doorbell.db
.tables
.schema leads
```

---

## Idempotency and tenant mapping

- **Idempotency**: Leads are deduplicated by `correlation_id`. If a webhook is received with the same `CorrelationId` again, the server returns `200` with `<success>ok</success>` and does **not** send another email.
- **Tenant mapping**: Each lead’s `ALAccountId` is looked up in `angi_mappings`. If found, that tenant is used. If not, the lead is assigned to the **tenant_default** tenant (seeded on first run), and a `mapped_to_default` event is recorded.

Seeded demo mappings:

- `ALAccountId` **123456** → `tenant_bob_plumbing` (anushkad@stanford.edu)
- `ALAccountId` **999999** → `tenant_alice_hvac` (anushkad@stanford.edu)
- Any other or missing `ALAccountId` → `tenant_default`

Emails can only be sent from verified sender emails via SendGrid. For the purposes of the demo, this is why I set the emails of both tenants to anushkad@stanford.edu

---

## Optional integrations

- **SendGrid**: Set `SENDGRID_API_KEY` to send real email; otherwise the email is printed to the console and an `outreach_messages` row is stored with status `mock_sent`.
- **OpenAI**: Set `USE_LLM_EMAIL=true` and `OPENAI_API_KEY` to draft outreach with the LLM; if unset or the call fails, a deterministic template is used.
