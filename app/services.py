"""Core logic: ingest Angi lead, dedupe, map tenant, persist, send outreach."""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.emailer import send_email
from app.llm import get_email_subject_and_body
from app.models import (
    Lead,
    LeadEvent,
    OutreachMessage,
    Tenant,
    AngiMapping,
    meta_to_str,
)
from app.schemas import AngiLeadWebhookPayload

logger = logging.getLogger(__name__)


def _find_tenant_for_al_account(db: Session, al_account_id: Optional[str]) -> Tenant:
    """Resolve tenant by ALAccountId; if missing, return tenant_default."""
    if al_account_id:
        mapping = (
            db.query(AngiMapping)
            .filter(
                AngiMapping.al_account_id == al_account_id,
                AngiMapping.active == True,
            )
            .first()
        )
        if mapping:
            return db.query(Tenant).filter(Tenant.id == mapping.tenant_id).first()
    default = db.query(Tenant).filter(Tenant.name == "tenant_default").first()
    if default:
        return default
    raise RuntimeError("tenant_default not found; run seed_demo_data first")


def _lead_from_payload(
    db: Session,
    payload: AngiLeadWebhookPayload,
    tenant: Tenant,
    raw_json: str,
) -> Lead:
    """Build Lead model from webhook payload."""
    addr = payload.PostalAddress
    return Lead(
        source="angi",
        correlation_id=payload.CorrelationId,
        al_account_id=payload.ALAccountId,
        tenant_id=tenant.id,
        first_name=payload.FirstName,
        last_name=payload.LastName,
        email=payload.Email,
        phone=payload.PhoneNumber,
        category=payload.Category,
        urgency=payload.Urgency,
        description=payload.Description,
        city=addr.City if addr else None,
        state=addr.State if addr else None,
        postal_code=addr.PostalCode if addr else None,
        raw_payload=raw_json,
        received_at=datetime.utcnow(),
    )


def _record_event(
    db: Session,
    lead_id: str,
    tenant_id: str,
    event_type: str,
    meta: Optional[dict] = None,
) -> None:
    ev = LeadEvent(
        lead_id=lead_id,
        tenant_id=tenant_id,
        event_type=event_type,
        event_ts=datetime.utcnow(),
        meta=meta_to_str(meta),
    )
    db.add(ev)


def process_angi_lead(
    db: Session,
    payload: AngiLeadWebhookPayload,
    raw_json: str,
) -> tuple[bool, Optional[str]]:
    """
    Idempotent processing: dedupe by correlation_id, map tenant, persist lead,
    compose and send email, record events.

    Returns:
        (is_duplicate, error_message)
        - If duplicate: True, None (caller returns 200 without sending again).
        - If error: False, error_message.
        - If success: False, None.
    """
    # 1) Dedupe: if lead with this correlation_id exists, treat as success (idempotent)
    existing = (
        db.query(Lead).filter(Lead.correlation_id == payload.CorrelationId).first()
    )
    if existing:
        return True, None

    # 2) Tenant mapping
    tenant = _find_tenant_for_al_account(db, payload.ALAccountId)
    used_default_tenant = tenant.name == "tenant_default"
    if used_default_tenant:
        logger.info(
            "angi_mapping missing for ALAccountId=%s; using tenant_default",
            payload.ALAccountId,
        )

    # 3) Persist lead
    try:
        lead = _lead_from_payload(db, payload, tenant, raw_json)
        db.add(lead)
        db.flush()
    except IntegrityError as e:
        if "correlation_id" in str(e).lower() or "unique" in str(e).lower():
            return True, None
        raise

    # 4) Events: received, mapped; if used default tenant, log mapped_to_default
    _record_event(db, lead.id, tenant.id, "received")
    _record_event(db, lead.id, tenant.id, "mapped")
    if used_default_tenant:
        _record_event(
            db,
            lead.id,
            tenant.id,
            "mapped_to_default",
            meta={"al_account_id": payload.ALAccountId},
        )
    db.commit()

    # 5) Compose email (LLM or template)
    subject, body = get_email_subject_and_body(
        tenant_name=tenant.name,
        first_name=lead.first_name,
        last_name=lead.last_name,
        category=lead.category,
        description=lead.description,
        city=lead.city,
        state=lead.state,
    )
    to_address = lead.email or "unknown@example.com"
    from_address = tenant.from_email

    # 6) Record email_queued
    _record_event(db, lead.id, tenant.id, "email_queued")

    # 7) Send email
    ok, provider_message_id, err_msg = send_email(
        to_address=to_address,
        from_address=from_address,
        subject=subject,
        body=body,
    )

    # 8) Persist outreach_messages row (status: sent, mock_sent, or failed)
    if ok:
        status = "mock_sent" if provider_message_id == "mock_sent" else "sent"
    else:
        status = "failed"
    msg = OutreachMessage(
        lead_id=lead.id,
        tenant_id=tenant.id,
        channel="email",
        to_address=to_address,
        from_address=from_address,
        subject=subject,
        body=body,
        status=status,
        provider_message_id=provider_message_id,
        sent_at=datetime.utcnow() if ok else None,
    )
    db.add(msg)
    db.commit()

    # 9) Events: email_sent or email_failed
    if ok:
        _record_event(db, lead.id, tenant.id, "email_sent", {"provider_message_id": provider_message_id})
    else:
        _record_event(db, lead.id, tenant.id, "email_failed", {"error": err_msg})
    db.commit()

    return False, None if ok else err_msg
