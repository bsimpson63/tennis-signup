# tennis-signup

Automates signing up for "Pro on Duty" tennis classes on [wac.clubautomation.com](https://wac.clubautomation.com).

## Setup

**1. Install dependencies**
```bash
./setup.sh
```

**2. Configure credentials**
```bash
cp .env.example .env
```
Edit `.env` and fill in your WAC username and password.

**3. Configure preferences**

Edit `config.py` to adjust:
- `CLASS_NAME` — class to search for (default: `"Pro on duty"`)
- `WEEKDAYS_ONLY` — skip weekend classes (default: `True`)
- `MORNING_ONLY` — skip afternoon classes (default: `True`)
- `DRY_RUN` — if `True`, finds a class but does not register (default: `True`)

**4. Test it**
```bash
python3 signup.py
```

With `DRY_RUN = True` the script will log which class it would register for without actually signing you up.

## Running automatically with launchd (macOS)

The included plist schedules the script to run daily at 12:01 AM.

**Install:**
```bash
cp com.bsimpson.tennis-signup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
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
launchctl unload ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
rm ~/Library/LaunchAgents/com.bsimpson.tennis-signup.plist
```

**Notes:**
- The job runs even if you're not logged in, but the Mac must be awake. If the Mac is asleep at 12:01 AM, launchd will run the job the next time it wakes.
- Logs are written to `signup.log` in the project directory.
- To change the run time, edit the `StartCalendarInterval` block in the plist and reload it.
