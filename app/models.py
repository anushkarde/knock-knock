"""SQLAlchemy ORM models for Knock Knock."""
import json
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    angi_mappings = relationship("AngiMapping", back_populates="tenant")
    leads = relationship("Lead", back_populates="tenant")
    outreach_messages = relationship("OutreachMessage", back_populates="tenant")
    lead_events = relationship("LeadEvent", back_populates="tenant")


class AngiMapping(Base):
    __tablename__ = "angi_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    al_account_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="angi_mappings")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="angi")
    correlation_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    al_account_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="leads")
    outreach_messages = relationship("OutreachMessage", back_populates="lead")
    lead_events = relationship("LeadEvent", back_populates="lead")


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="email")
    to_address: Mapped[str] = mapped_column(String(255), nullable=False)
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    lead = relationship("Lead", back_populates="outreach_messages")
    tenant = relationship("Tenant", back_populates="outreach_messages")


class LeadEvent(Base):
    __tablename__ = "lead_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("leads.id"), nullable=False
    )
    tenant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    meta: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    lead = relationship("Lead", back_populates="lead_events")
    tenant = relationship("Tenant", back_populates="lead_events")


def meta_to_str(data: Any) -> str:
    """Serialize meta dict to TEXT for storage."""
    if data is None:
        return ""
    return json.dumps(data) if isinstance(data, dict) else str(data)
