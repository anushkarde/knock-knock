"""Send email via SendGrid or console fallback for Knock Knock."""
from typing import Optional

from app.config import SENDGRID_API_KEY


def send_email(
    *,
    to_address: str,
    from_address: str,
    subject: str,
    body: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Send email via SendGrid if SENDGRID_API_KEY is set; otherwise print to console.

    Returns:
        (success, provider_message_id, error_message)
    """
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(
            to_address=to_address,
            from_address=from_address,
            subject=subject,
            body=body,
        )
    return _send_via_console(
        to_address=to_address,
        from_address=from_address,
        subject=subject,
        body=body,
    )


def _send_via_sendgrid(
    *,
    to_address: str,
    from_address: str,
    subject: str,
    body: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=from_address,
            to_emails=to_address,
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        msg_id = response.headers.get("X-Message-Id") or str(response.status_code)
        return True, msg_id, None
    except Exception as e:
        return False, None, str(e)


def _send_via_console(
    *,
    to_address: str,
    from_address: str,
    subject: str,
    body: str,
) -> tuple[bool, Optional[str], Optional[str]]:
    print("--- EMAIL (console fallback) ---")
    print(f"From: {from_address}")
    print(f"To: {to_address}")
    print(f"Subject: {subject}")
    print("-" * 40)
    print(body)
    print("--- END EMAIL ---")
    return True, "mock_sent", None
