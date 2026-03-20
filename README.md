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
  "class_names": [
    "Pro On Duty Advanced Monday AM",
    "Stroke of the Week Wednesday AM"
  ],
  "dry_run": false
}
```
Class names are case-insensitive partial matches against what appears on the [class calendar](https://wac.clubautomation.com/calendar/classes?tab=by-date). Include the day in the name (e.g. "Monday AM") to avoid matching classes on the wrong day.

**4. Test it**
```bash
python3 signup.py
```

## How it works

1. Runs nightly at 12:01 AM
2. Logs in via Selenium (Chromium, headless) and navigates to the by-date calendar view
3. Finds the first open class whose name matches any configured class name
4. Clicks Sign Up, selects the member, and adds to cart
5. Calls CapSolver to solve the Cloudflare Turnstile challenge on the cart page
6. POSTs directly to the payment API using the session cookies + Turnstile token

## Web UI

A Flask web app lets you manage the class list and view logs from any browser on your local network.

**Access at:** `http://raspberrypi.local:5000`

The web UI lets you:
- Add and remove class names
- Toggle dry run mode
- View recent log output

## Running automatically on Raspberry Pi

### Signup script — cron

```bash
crontab -e
```
Add:
```
1 0 * * * cd /home/pi/tennis-signup && /home/pi/tennis-signup/venv/bin/python3 signup.py >> /home/pi/tennis-signup/signup.log 2>&1
```

### Web UI — systemd

The web app runs as a systemd service so it starts on boot and restarts automatically if it crashes.

**Install:**
```bash
sudo cp tennis-webapp.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tennis-webapp
sudo systemctl start tennis-webapp
```

**Status / logs:**
```bash
sudo systemctl status tennis-webapp
sudo journalctl -u tennis-webapp -f
```

**Restart:**
```bash
sudo systemctl restart tennis-webapp
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
