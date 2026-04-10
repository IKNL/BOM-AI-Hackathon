import os
from pathlib import Path

_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "medium")
WHISPER_LANGUAGE = os.environ.get("WHISPER_LANGUAGE", "nl")
