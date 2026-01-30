"""Seed demo data for Knock Knock (tenants + angi_mappings)."""
from sqlalchemy.orm import Session

from app.models import AngiMapping, Tenant


def seed_demo_data(db: Session) -> None:
    """Create default tenants and angi_mappings if tables are empty."""
    if db.query(Tenant).first() is not None:
        return

    t_default = Tenant(
        id="tenant_default",
        name="tenant_default",
        from_email="noreply@knockknock.example.com",
        timezone="America/New_York",
    )
    t_bob = Tenant(
        name="tenant_bob_plumbing",
        from_email="bob@example.com",
        timezone="America/New_York",
    )
    t_alice = Tenant(
        name="tenant_alice_hvac",
        from_email="alice@example.com",
        timezone="America/New_York",
    )
    db.add(t_default)
    db.add(t_bob)
    db.add(t_alice)
    db.flush()

    db.add(
        AngiMapping(
            al_account_id="123456",
            tenant_id=t_bob.id,
            active=True,
        )
    )
    db.add(
        AngiMapping(
            al_account_id="999999",
            tenant_id=t_alice.id,
            active=True,
        )
    )
    db.commit()
