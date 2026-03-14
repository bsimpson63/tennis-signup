# tennis-signup

Automates signing up for "Pro on Duty Advanced" tennis classes on [wac.clubautomation.com](https://wac.clubautomation.com).

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

**3. Configure preferences**

Edit `config.py` to adjust:
- `CLASS_NAME` — class to search for (default: `"Pro on duty advanced"`)
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

1. Logs in via Playwright (Chromium)
2. Navigates to the by-date calendar view and finds the soonest open matching class
3. Clicks Sign Up, selects the member, and adds to cart
4. Calls CapSolver to solve the Cloudflare Turnstile challenge on the cart page
5. POSTs directly to the payment API using the session cookies + Turnstile token

## Running automatically with launchd (macOS)

The included plist schedules the script to run daily at 12:01 AM.

**Install:**
```bash
cp com.bsimpson.tennis-signup.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
```

**Verify it's loaded:**
```bash
launchctl list | grep tennis
```

**Check logs:**
```bash
tail -f /Users/bsimpson/projects/tennis-signup/signup.log
```

**Uninstall:**
```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
rm ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
```

**Notes:**
- The Mac must be awake at 12:01 AM. If it's asleep, launchd will run the job the next time it wakes.
- Logs are written to `signup.log` in the project directory.
- To change the run time, edit the `StartCalendarInterval` block in the plist, then reload:
  ```bash
  launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
  ```
