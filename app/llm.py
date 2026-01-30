"""Optional OpenAI email drafting with template fallback for Knock Knock."""
from typing import Optional

from app.config import OPENAI_API_KEY, USE_LLM_EMAIL


def draft_email_with_llm(
    *,
    tenant_name: str,
    first_name: Optional[str],
    last_name: Optional[str],
    category: Optional[str],
    description: Optional[str],
    city: Optional[str],
    state: Optional[str],
) -> Optional[str]:
    """
    Draft a short outreach email using OpenAI if USE_LLM_EMAIL and OPENAI_API_KEY are set.
    Returns None on failure or when LLM is disabled (caller should use template).
    """
    if not USE_LLM_EMAIL or not OPENAI_API_KEY:
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        name = " ".join(filter(None, [first_name, last_name])) or "there"
        prompt = f"""Write a brief, professional outreach email (2-3 sentences) from {tenant_name} to a lead named {name}.
Category: {category or 'N/A'}
Description: {description or 'N/A'}
Location: {city or ''} {state or ''}. Do not use placeholders; write a real short email body only, no subject line."""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        if resp.choices and resp.choices[0].message and resp.choices[0].message.content:
            return resp.choices[0].message.content.strip()
    except Exception:
        pass
    return None


def get_email_subject_and_body(
    *,
    tenant_name: str,
    first_name: Optional[str],
    last_name: Optional[str],
    category: Optional[str],
    description: Optional[str],
    city: Optional[str],
    state: Optional[str],
) -> tuple[str, str]:
    """
    Return (subject, body). Uses LLM if available; otherwise deterministic template.
    """
    body_llm = draft_email_with_llm(
        tenant_name=tenant_name,
        first_name=first_name,
        last_name=last_name,
        category=category,
        description=description,
        city=city,
        state=state,
    )
    name = " ".join(filter(None, [first_name, last_name])) or "there"
    if body_llm:
        subject = f"Hi {name} – {tenant_name} following up"
        return subject, body_llm
    # Template fallback
    subject = f"Quick follow-up from {tenant_name}"
    body = f"Hi {name},\n\nThanks for your interest. We received your request"
    if category:
        body += f" for {category}"
    body += " and would like to help."
    if description:
        body += f"\n\nWe'll review your details and get back to you soon."
    body += "\n\nBest,\n" + tenant_name
    return subject, body
