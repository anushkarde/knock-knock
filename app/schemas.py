"""Pydantic request/response models for Knock Knock (Angi lead webhook)."""
from typing import Optional

from pydantic import BaseModel, Field


class PostalAddressSchema(BaseModel):
    """Angi postal address in webhook payload."""

    AddressFirstLine: Optional[str] = None
    AddressSecondLine: Optional[str] = None
    City: Optional[str] = None
    State: Optional[str] = None
    PostalCode: Optional[str] = None


class AngiLeadWebhookPayload(BaseModel):
    """Angi lead webhook JSON body."""

    CorrelationId: str = Field(..., description="Unique idempotency key for the lead")
    ALAccountId: Optional[str] = None
    Email: Optional[str] = None
    PhoneNumber: Optional[str] = None
    FirstName: Optional[str] = None
    LastName: Optional[str] = None
    Description: Optional[str] = None
    Category: Optional[str] = None
    Urgency: Optional[str] = None
    PostalAddress: Optional[PostalAddressSchema] = None
