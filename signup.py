#!/usr/bin/env python3
"""
Tennis class signup script for wac.clubautomation.com.
Targets the "by-class" calendar tab and registers for a named class.
"""

import sys
import re
import config
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://wac.clubautomation.com"
CLASSES_URL = f"{BASE_URL}/calendar/classes"

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
WEEKENDS = {"saturday", "sunday"}

# Time patterns like "9:00 AM", "11:30 AM", "1:00 PM"
TIME_RE = re.compile(r'(\d{1,2}:\d{2}\s*(AM|PM))', re.IGNORECASE)


def log(msg):
    print(f"[tennis-signup] {msg}")


def is_before_noon(text):
    """Return True if any time found in text is before 12:00 PM."""
    for match in TIME_RE.finditer(text):
        time_str = match.group(0).strip().upper()
        if "AM" in time_str:
            return True
        if "PM" in time_str:
            hour = int(time_str.split(":")[0])
            if hour == 12:
                return True  # 12:00 PM is noon — treat as not before noon
            return False
    # If no time found, fall back to checking for "AM"/"PM" in class title
    title_upper = text.upper()
    if " AM" in title_upper:
        return True
    if " PM" in title_upper:
        return False
    return True  # no time info — don't filter out


def is_weekday(text):
    """Return True if the class title/text mentions a weekday."""
    text_lower = text.lower()
    for day in WEEKDAYS:
        if day in text_lower:
            return True
    for day in WEEKENDS:
        if day in text_lower:
            return False
    return True  # no day found — don't filter out


def login(page):
    log("Navigating to login page...")
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    log("Filling credentials...")
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

    log(f"Logged in. Current URL: {page.url}")


def load_classes_page(page):
    log("Navigating to Group Activities / Classes...")

    nav_candidates = [
        "a:has-text('Group Activities')",
        "a:has-text('Classes')",
        "a:has-text('Programs')",
        "a:has-text('Calendar')",
    ]

    for sel in nav_candidates:
        try:
            links = page.locator(sel).all()
            for link in links:
                href = link.get_attribute("href") or ""
                text = link.inner_text(timeout=1000).strip()
                if any(kw in href.lower() or kw in text.lower()
                       for kw in ["class", "group", "calendar", "activity"]):
                    log(f"  Clicking: '{text}'")
                    link.click()
                    page.wait_for_load_state("networkidle")
                    log(f"  Navigated to: {page.url}")

                    # Click the "By Class" tab
                    try:
                        tab = page.locator(
                            "#byClassTab, [data-tab='by-class'], "
                            "a:has-text('By Class'), li:has-text('By Class')"
                        ).first
                        tab.wait_for(state="visible", timeout=5000)
                        tab.click()
                        page.wait_for_load_state("networkidle")
                        log("  Switched to 'By Class' tab.")
                    except PlaywrightTimeoutError:
                        pass

                    return
        except PlaywrightTimeoutError:
            continue

    log("Could not find the classes nav link.")
    sys.exit(1)


def try_register_on_detail_page(page):
    """
    On the class detail page/modal, find and click an open register button.
    Returns the button element if found, else None.
    """
    disabled = {"full", "not yet open", "closed", "cancel", "registered", "waitlist"}

    for btn_sel in [
        ".register_button",
        ".register-button-now",
        "a:has-text('Register')",
        "button:has-text('Register')",
        "input[value='Register']",
    ]:
        try:
            for btn in page.locator(btn_sel).all():
                if not btn.is_visible(timeout=500):
                    continue
                label = (btn.inner_text(timeout=500).strip()
                         or btn.get_attribute("value") or "").lower()
                if label in disabled:
                    continue
                return btn
        except PlaywrightTimeoutError:
            continue

    return None


def find_and_register(page):
    log(f"Searching for '{config.CLASS_NAME}' classes"
        + (" (weekdays only)" if config.WEEKDAYS_ONLY else "")
        + (" (before noon only)" if config.MORNING_ONLY else ""))

    try:
        page.wait_for_selector(".row_link", timeout=config.TIMEOUT * 1000)
    except PlaywrightTimeoutError:
        log(f"No class rows found. Current URL: {page.url}")
        return False

    row_links = page.locator(".row_link")
    count = row_links.count()
    log(f"Found {count} total class entries on page.")

    classes_url = page.url  # remember so we can return after visiting detail pages

    for i in range(count):
        row_link = row_links.nth(i)
        try:
            title = row_link.inner_text(timeout=2000).strip()
        except PlaywrightTimeoutError:
            continue

        # Name filter
        if config.CLASS_NAME.lower() not in title.lower():
            continue

        # Weekday filter
        if config.WEEKDAYS_ONLY and not is_weekday(title):
            log(f"  Skipping (weekend): {title}")
            continue

        # Before-noon filter
        if config.MORNING_ONLY and not is_before_noon(title):
            log(f"  Skipping (afternoon): {title}")
            continue

        log(f"  Candidate: '{title}'")

        # Click into the class detail page/modal
        try:
            row_link.click(timeout=5000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)
        except Exception as e:
            log(f"  Could not open detail page: {e}")
            continue

        register_btn = try_register_on_detail_page(page)

        if register_btn is None:
            log("  No open register button (full / not yet open). Skipping.")
            # Close modal or go back
            try:
                close = page.locator("button:has-text('close'), .modal-close, [aria-label='Close']").first
                if close.is_visible(timeout=1000):
                    close.click()
                    page.wait_for_timeout(500)
                else:
                    page.go_back()
                    page.wait_for_load_state("networkidle")
            except Exception:
                page.go_back()
                page.wait_for_load_state("networkidle")
            continue

        btn_label = register_btn.inner_text().strip() or "Register"

        if config.DRY_RUN:
            log(f"  DRY RUN: Would click '{btn_label}'. Set DRY_RUN = False in config.py to register.")
            return True

        log(f"  Clicking '{btn_label}'...")
        register_btn.click()
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
                btn = page.locator(confirm_sel).first
                if btn.is_visible(timeout=3000):
                    log(f"  Confirming...")
                    btn.click()
                    page.wait_for_load_state("networkidle")
                    break
            except PlaywrightTimeoutError:
                continue

        if page.locator(".registered-green, .success, .alert-success").count() > 0:
            log(f"Successfully registered for '{title}'!")
        else:
            log(f"Registration submitted for '{title}'. Please verify in your account.")

        return True

    log("No eligible class found with an open registration slot.")
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(config.TIMEOUT * 1000)

        try:
            login(page)
            load_classes_page(page)
            find_and_register(page)
        except Exception as e:
            log(f"Error: {e}")
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
