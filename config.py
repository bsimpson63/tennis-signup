# Configuration for tennis class signup
import os
import json
import pathlib

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
CAPSOLVER_API_KEY = os.environ.get("CAPSOLVER_API_KEY", "")
MEMBER_USER_ID = os.environ.get("MEMBER_USER_ID", "")
PAYMENT_ACCOUNT = os.environ.get("PAYMENT_ACCOUNT", "")
BILL_STREET_ADDRESS = os.environ.get("BILL_STREET_ADDRESS", "")
BILL_CITY = os.environ.get("BILL_CITY", "")
BILL_STATE = os.environ.get("BILL_STATE", "")

# Optional: set these to use a specific Chromium/ChromeDriver (e.g. on Raspberry Pi)
# Leave empty to let Selenium auto-detect (works on Mac with Chrome installed)
CHROMIUM_PATH = os.environ.get("CHROMIUM_PATH", "")
CHROMEDRIVER_PATH = os.environ.get("CHROMEDRIVER_PATH", "")

if not USERNAME or not PASSWORD:
    raise RuntimeError("WAC_USERNAME and WAC_PASSWORD must be set in .env or the environment.")
if not CAPSOLVER_API_KEY:
    raise RuntimeError("CAPSOLVER_API_KEY must be set in .env or the environment.")

# Load user settings from settings.json (managed via web UI)
_settings_path = pathlib.Path(__file__).parent / "settings.json"
_settings = {}
if _settings_path.exists():
    try:
        _settings = json.loads(_settings_path.read_text())
    except Exception:
        pass

# Schedule: list of {"class_name": str, "day": str} dicts — managed via web UI
# Example: [{"class_name": "Pro On Duty Advanced Monday AM", "day": "monday"}]
SCHEDULES = _settings.get("schedules", [])

# If True, finds and prints the class but does NOT register
DRY_RUN = _settings.get("dry_run", False)

# If True, runs through add-to-cart and captcha solving but skips payment submission
CAPTCHA_TEST_ONLY = False

# Page load timeout in seconds
TIMEOUT = 30

# Cloudflare Turnstile site key for wac.clubautomation.com cart checkout (do not change)
CF_TURNSTILE_SITE_KEY = "0x4AAAAAAA_si1yPhVGYVyBi"
CF_TURNSTILE_URL = "https://wac.clubautomation.com/member/cart"
