#!/usr/bin/env python3
"""
Tennis class signup script for wac.clubautomation.com.
Uses the by-date calendar view to find open "Pro on Duty" slots and register.
"""

import sys
import re
import config
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://wac.clubautomation.com"

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}

TIME_RE = re.compile(r'(\d{1,2}:\d{2})(am|pm)', re.IGNORECASE)


def log(msg):
    print(f"[tennis-signup] {msg}")


def is_before_noon(time_str):
    """Return True if a time string like '09:00am' or '11:30am' is before noon."""
    m = TIME_RE.search(time_str)
    if not m:
        return True  # no time found, don't filter out
    hour = int(m.group(1).split(":")[0])
    period = m.group(2).lower()
    if period == "am":
        return True
    # PM: only 12:00pm counts as noon (not before noon)
    return False


def login(page):
    log("Logging in...")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")
    page.locator('input[name="login"]').fill(config.USERNAME)
    page.locator('input[name="password"]').fill(config.PASSWORD)
    page.locator('input[type="submit"], button[type="submit"]').first.click()
    try:
        page.wait_for_url("**/member**", timeout=config.TIMEOUT * 1000)
    except PlaywrightTimeoutError:
        pass
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    if page.locator(".error, .alert-danger").count() > 0:
        try:
            err = page.locator(".error, .alert-danger").first.inner_text(timeout=2000)
            log(f"Login failed: {err}")
        except PlaywrightTimeoutError:
            pass
        sys.exit(1)

    log(f"Logged in. URL: {page.url}")


def load_by_date_view(page):
    log("Navigating to Group Activities (by-date view)...")
    page.locator("a:has-text('Group Activities')").first.click()
    page.wait_for_load_state("networkidle")

    try:
        tab = page.locator(
            "#byDateTab, [data-tab='by-date'], a:has-text('By Date'), li:has-text('By Date')"
        ).first
        tab.wait_for(state="visible", timeout=5000)
        tab.click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)
        log(f"Switched to By Date view. URL: {page.url}")
    except PlaywrightTimeoutError:
        log("By Date tab not found, may already be active.")


def find_and_register(page):
    log(f"Searching for open '{config.CLASS_NAME}' classes"
        + (" (weekdays only)" if config.WEEKDAYS_ONLY else "")
        + (" (before noon only)" if config.MORNING_ONLY else ""))

    try:
        page.wait_for_selector("div.block", timeout=config.TIMEOUT * 1000)
    except PlaywrightTimeoutError:
        log(f"No class entries found on page. URL: {page.url}")
        return False

    # Each class entry is a div.block containing the title, time, and register button.
    # Find blocks that have an open (non-closed) register button.
    blocks = page.locator("div.block:has(.register_button:not(.register-button-closed))").all()
    log(f"Found {len(blocks)} class(es) with open registration.")

    for block in blocks:
        container_text = block.inner_text(timeout=2000).strip()

        # Name filter
        if config.CLASS_NAME.lower() not in container_text.lower():
            continue

        # Extract the class title line
        title = ""
        for line in container_text.splitlines():
            line = line.strip()
            if config.CLASS_NAME.lower() in line.lower():
                title = line
                break

        # Weekday filter
        if config.WEEKDAYS_ONLY:
            if not any(day in container_text.lower() for day in WEEKDAYS):
                log(f"  Skipping (weekend): {title}")
                continue

        # Before-noon filter
        if config.MORNING_ONLY:
            time_match = TIME_RE.search(container_text)
            time_str = time_match.group(0) if time_match else ""
            if not is_before_noon(time_str):
                log(f"  Skipping (afternoon): {title}")
                continue

        btn = block.locator(".register_button:not(.register-button-closed)").first
        btn_label = btn.inner_text(timeout=1000).strip() or "Sign Up"
        log(f"  Found open class: '{title}' — button says '{btn_label}'")

        if config.DRY_RUN:
            log("  DRY RUN: Would register. Set DRY_RUN = False in config.py to sign up.")
            return True

        log(f"  Clicking '{btn_label}'...")
        btn.click()
        page.wait_for_load_state("networkidle")

        # Confirm any modal/dialog
        for confirm_sel in [
            "button:has-text('Confirm')",
            "button:has-text('Submit')",
            "button:has-text('Complete Registration')",
            "input[value='Confirm']",
            "input[value='Submit']",
            ".confirm-button",
        ]:
            try:
                confirm = page.locator(confirm_sel).first
                if confirm.is_visible(timeout=3000):
                    log("  Confirming...")
                    confirm.click()
                    page.wait_for_load_state("networkidle")
                    break
            except PlaywrightTimeoutError:
                continue

        if page.locator(".registered-green, .success, .alert-success").count() > 0:
            log(f"Successfully registered for '{title}'!")
        else:
            log(f"Registration submitted for '{title}'. Please verify in your account.")

        return True

    log("No open Pro on Duty AM weekday classes found today.")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(config.TIMEOUT * 1000)

        try:
            login(page)
            load_by_date_view(page)
            find_and_register(page)
        except Exception as e:
            log(f"Error: {e}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
