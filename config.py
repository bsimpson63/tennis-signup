# Configuration for tennis class signup
import os, pathlib

# Load .env file if present (no external dependencies)
_env = pathlib.Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

USERNAME = os.environ.get("WAC_USERNAME", "")
PASSWORD = os.environ.get("WAC_PASSWORD", "")

if not USERNAME or not PASSWORD:
    raise RuntimeError("WAC_USERNAME and WAC_PASSWORD must be set in .env or the environment.")

# Class to sign up for (case-insensitive, partial match on class title)
CLASS_NAME = "Pro on duty"

# Only register for weekday classes (Mon-Fri). Set to False to include weekends.
WEEKDAYS_ONLY = True

# Only register for morning classes (before noon). Set to False to include afternoons.
MORNING_ONLY = True

# If True, finds and prints the class but does NOT register
DRY_RUN = True

# Page load timeout in seconds
TIMEOUT = 30
