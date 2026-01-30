"""Environment and settings for Knock Knock."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env: cwd first, then project root with override so project .env wins over shell/cwd
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv()
load_dotenv(_env_path, override=True)


def _str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _bool(key: str, default: bool = False) -> bool:
    val = _str(key).lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# Database
DATABASE_URL = _str("DATABASE_URL") or "sqlite:///./doorbell.db"

# Angi webhook
ANGI_API_KEY = _str("ANGI_API_KEY")


# SendGrid (optional)
SENDGRID_API_KEY = _str("SENDGRID_API_KEY")

# OpenAI (optional)
OPENAI_API_KEY = _str("OPENAI_API_KEY")
USE_LLM_EMAIL = _bool("USE_LLM_EMAIL", default=False)
