# tennis-signup

Automates signing up for tennis classes on [wac.clubautomation.com](https://wac.clubautomation.com).

## Setup

**1. Install dependencies**
```bash
./setup.sh
```

**2. Configure credentials**
```bash
cp .env.example .env
```
Edit `.env` and fill in all required values:
- `WAC_USERNAME` / `WAC_PASSWORD` — your club login
- `CAPSOLVER_API_KEY` — from [capsolver.com](https://capsolver.com) (used to solve the Cloudflare Turnstile on checkout)
- `MEMBER_USER_ID` — your numeric member ID (find in Chrome DevTools when submitting payment)
- `PAYMENT_ACCOUNT` — your saved payment method identifier (e.g. `user-credit-card_XXXXX`)
- `BILL_STREET_ADDRESS`, `BILL_CITY`, `BILL_STATE` — billing address
- `CHROMIUM_PATH` / `CHROMEDRIVER_PATH` — optional; set these on Raspberry Pi (e.g. `/usr/bin/chromium`, `/usr/bin/chromedriver`). Leave unset on Mac to use selenium-manager auto-detection.

**3. Configure your schedule**

Start the web UI and add classes via the browser (see below), or manually create `settings.json`:
```json
{
  "schedules": [
    {"class_name": "Pro On Duty Advanced Monday AM", "day": "monday"},
    {"class_name": "Stroke of the Week Wednesday AM", "day": "wednesday"}
  ],
  "dry_run": false
}
```
Class names are case-insensitive partial matches against what appears on the [class calendar](https://wac.clubautomation.com/calendar/classes?tab=by-date).

**4. Test it**
```bash
python3 signup.py
```

## How it works

1. Runs nightly at 12:01 AM
2. Checks today's day of week against the configured schedule
3. Logs in via Selenium (Chromium, headless) and navigates to the by-date calendar view
4. Finds the first open class matching today's scheduled class name
5. Clicks Sign Up, selects the member, and adds to cart
6. Calls CapSolver to solve the Cloudflare Turnstile challenge on the cart page
7. POSTs directly to the payment API using the session cookies + Turnstile token

## Web UI

A Flask web app lets you manage the schedule and view logs from any browser on your local network.

**Start manually:**
```bash
python3 webapp.py
```

**Access at:** `http://raspberrypi.local:5000` (or the Pi's IP address)

The web UI lets you:
- Add and remove (class name, day) schedule entries
- Toggle dry run mode
- View recent log output

The web app starts automatically on boot via cron (`@reboot`).

## Running automatically

### Raspberry Pi (recommended) — cron

```bash
crontab -e
```
Add:
```
1 0 * * * cd /home/pi/tennis-signup && /home/pi/tennis-signup/venv/bin/python3 signup.py >> /home/pi/tennis-signup/signup.log 2>&1
@reboot cd /home/pi/tennis-signup && /home/pi/tennis-signup/venv/bin/python3 webapp.py >> /home/pi/tennis-signup/webapp.log 2>&1
```

### macOS — launchd

`setup.sh` generates a `com.tennis-signup.plist` file with the correct paths for your machine. Run it first if you haven't already.

**Install:**
```bash
cp com.tennis-signup.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.tennis-signup.plist
```

**Uninstall:**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.tennis-signup.plist
rm ~/Library/LaunchAgents/com.tennis-signup.plist
```

## Checking logs

```bash
tail -f signup.log
```
