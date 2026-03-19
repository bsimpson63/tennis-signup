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

**3. Configure preferences**

Edit `config.py` to adjust:
- `CLASS_NAMES` — list of classes to search for (registers for the first available match)
- `WEEKDAYS_ONLY` — skip weekend classes (default: `True`)
- `MORNING_ONLY` — skip afternoon classes (default: `True`)
- `DRY_RUN` — if `True`, finds a class but does not register (default: `False`)
- `CAPTCHA_TEST_ONLY` — if `True`, runs through add-to-cart and captcha solving but skips payment submission (default: `False`)

**4. Test it**
```bash
python3 signup.py
```

With `DRY_RUN = True` the script will log which class it would register for without actually signing you up.

## How it works

1. Logs in via Selenium (Chromium, headless)
2. Navigates to the by-date calendar view and finds the soonest open matching class
3. Clicks Sign Up, selects the member, and adds to cart
4. Calls CapSolver to solve the Cloudflare Turnstile challenge on the cart page
5. POSTs directly to the payment API using the session cookies + Turnstile token

## Running automatically

### Raspberry Pi (recommended) — cron

```bash
crontab -e
```
Add:
```
1 0 * * * cd /home/pi/tennis-signup && /home/pi/tennis-signup/venv/bin/python3 signup.py >> /home/pi/tennis-signup/signup.log 2>&1
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

**Notes:**
- The Mac must be awake at 12:01 AM. If it's asleep, launchd will run the job the next time it wakes.
- To change the run time, edit the `StartCalendarInterval` block in the plist, then reload it.

## Checking logs

```bash
tail -f signup.log
```
