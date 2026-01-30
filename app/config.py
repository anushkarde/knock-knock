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


def _angi_api_key_from_project_env() -> str:
    """Read ANGI_API_KEY from project .env so it wins over shell env (e.g. 25-char key elsewhere)."""
    if not _env_path.exists():
        return ""
    try:
        text = _env_path.read_text()
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("ANGI_API_KEY=") and not line.startswith("ANGI_API_KEY=#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return val
    except Exception:
        pass
    return ""


def _bool(key: str, default: bool = False) -> bool:
    val = _str(key).lower()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# Database
DATABASE_URL = _str("DATABASE_URL") or "sqlite:///./doorbell.db"

# Angi webhook (prefer project .env over shell so project key always wins)
ANGI_API_KEY = _angi_api_key_from_project_env() or _str("ANGI_API_KEY")


# SendGrid (optional)
SENDGRID_API_KEY = _str("SENDGRID_API_KEY")

# OpenAI (optional)
OPENAI_API_KEY = _str("OPENAI_API_KEY")
USE_LLM_EMAIL = _bool("USE_LLM_EMAIL", default=False)
