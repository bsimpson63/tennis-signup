#!/usr/bin/env python3
"""
Tennis class signup script for wac.clubautomation.com.
Uses the by-date calendar view to find open "Pro on Duty" slots and register.
Checkout is completed via direct API call with a CapSolver-generated Turnstile token.
"""

import sys
import re
import requests
import capsolver
import config
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://wac.clubautomation.com"

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday"}
TIME_RE = re.compile(r'(\d{1,2}:\d{2})(am|pm)', re.IGNORECASE)


def log(msg):
    print(f"[tennis-signup] {msg}")


def is_before_noon(time_str):
    m = TIME_RE.search(time_str)
    if not m:
        return True
    period = m.group(2).lower()
    if period == "am":
        return True
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


def add_to_cart(page, title):
    """Click Sign Up, select member, add to cart. Returns True on success."""
    log(f"  Clicking 'Sign Up'...")
    page.wait_for_timeout(500)

    # Click opens /calendar/event-sign-up-popup modal
    page.evaluate("""() => {
        const btn = document.querySelector('.register_button:not(.register-button-closed):not(.register-button-incart)');
        if (btn) btn.click();
    }""")

    # Wait for the popup members list
    try:
        page.wait_for_selector(".members-list", timeout=10000)
    except PlaywrightTimeoutError:
        log("  Popup members list not found.")
        return False

    # Select the first approved member
    selected = page.evaluate("""() => {
        const member = document.querySelector('.select-member.approved');
        if (!member) return null;
        member.click();
        return member.querySelector('span[id$="-name"]').textContent.trim();
    }""")
    if not selected:
        log("  No approved member found in popup.")
        return False
    log(f"  Selected member: {selected}")
    page.wait_for_timeout(500)

    # Click Add to Cart
    page.evaluate("document.querySelector('#add-to-cart').click()")

    # Wait for cart count to increment
    try:
        page.wait_for_function(
            "() => !document.querySelector('.view_cart_text').innerText.includes('(0)')",
            timeout=8000
        )
    except PlaywrightTimeoutError:
        log("  Cart did not update after clicking Add to Cart.")
        return False

    cart_text = page.locator(".view_cart_text").inner_text(timeout=2000)
    log(f"  Cart updated: '{cart_text}'")
    return True


def get_cart_item_id(page):
    """Navigate to cart page and extract the cart item ID from the page HTML."""
    page.goto(f"{BASE_URL}/member/cart")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    html = page.content()
    match = re.search(r'/cart_items/(\d+)/', html)
    if match:
        cart_item_id = match.group(1)
        log(f"  Cart item ID: {cart_item_id}")
        return cart_item_id

    log("  Could not find cart item ID in cart page HTML.")
    return None


def solve_turnstile():
    """Use CapSolver to solve the Cloudflare Turnstile challenge."""
    log("  Solving Cloudflare Turnstile via CapSolver...")
    capsolver.api_key = config.CAPSOLVER_API_KEY
    solution = capsolver.solve({
        "type": "AntiCloudflareTask",
        "websiteURL": config.CF_TURNSTILE_URL,
        "websiteKey": config.CF_TURNSTILE_SITE_KEY,
    })
    token = solution.get("token")
    if token:
        log("  Turnstile solved.")
    else:
        log(f"  CapSolver returned unexpected response: {solution}")
    return token


def submit_payment(page, cart_item_id, turnstile_token):
    """POST the payment directly using the session cookies from Playwright."""
    # Extract session cookies
    cookies = {c["name"]: c["value"] for c in page.context.cookies()}

    url = (f"{BASE_URL}/member/cart/step/1/cart_items/{cart_item_id}/"
           f"?ajax=1&ajax=true")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "X-Prototype-Version": "1.7",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/member/cart",
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/137.0.0.0 Safari/537.36"),
    }

    payload = {
        "ajax": "1",
        "active_gateway": "CashFlow",
        "user_id": config.MEMBER_USER_ID,
        "continue": "1",
        "account": config.PAYMENT_ACCOUNT,
        "bill_street_address": config.BILL_STREET_ADDRESS,
        "bill_city": config.BILL_CITY,
        "bill_state": config.BILL_STATE,
        "captcha-site-key": config.CF_TURNSTILE_SITE_KEY,
        "cf-turnstile-response": turnstile_token,
    }

    log(f"  Submitting payment to {url}...")
    response = requests.post(url, data=payload, cookies=cookies, headers=headers, timeout=30)
    log(f"  Response: {response.status_code}")
    log(f"  Response body: {response.text[:500]}")
    return response


def find_and_register(page):
    log(f"Searching for open '{config.CLASS_NAME}' classes"
        + (" (weekdays only)" if config.WEEKDAYS_ONLY else "")
        + (" (before noon only)" if config.MORNING_ONLY else ""))

    try:
        page.wait_for_selector("div.block", timeout=config.TIMEOUT * 1000)
    except PlaywrightTimeoutError:
        log(f"No class entries found on page. URL: {page.url}")
        return False

    blocks = page.locator("div.block:has(.register_button:not(.register-button-closed))").all()
    log(f"Found {len(blocks)} class(es) with open registration.")

    for block in blocks:
        container_text = block.inner_text(timeout=2000).strip()

        if config.CLASS_NAME.lower() not in container_text.lower():
            continue

        title = ""
        for line in container_text.splitlines():
            line = line.strip()
            if config.CLASS_NAME.lower() in line.lower():
                title = line
                break

        if config.WEEKDAYS_ONLY:
            if not any(day in container_text.lower() for day in WEEKDAYS):
                log(f"  Skipping (weekend): {title}")
                continue

        if config.MORNING_ONLY:
            time_match = TIME_RE.search(container_text)
            time_str = time_match.group(0) if time_match else ""
            if not is_before_noon(time_str):
                log(f"  Skipping (afternoon): {title}")
                continue

        btn = block.locator(".register_button:not(.register-button-closed)").first
        btn_label = btn.inner_text(timeout=1000).strip() or "Sign Up"

        if "in cart" in btn_label.lower():
            log(f"  Skipping '{title}' — already in cart. Clear your cart at /member/cart first.")
            continue

        log(f"  Found open class: '{title}'")

        if config.DRY_RUN:
            log("  DRY RUN: Would register. Set DRY_RUN = False in config.py to sign up.")
            return True

        # Step 1: add to cart via popup
        btn.scroll_into_view_if_needed()
        btn.click()
        if not add_to_cart(page, title):
            continue

        # Step 2: get cart item ID
        cart_item_id = get_cart_item_id(page)
        if not cart_item_id:
            continue

        # Step 3: solve Turnstile
        turnstile_token = solve_turnstile()
        if not turnstile_token:
            log("  Failed to get Turnstile token from CapSolver.")
            return False

        # Step 4: submit payment directly via requests
        response = submit_payment(page, cart_item_id, turnstile_token)

        if response.status_code == 200:
            log(f"Successfully registered for '{title}'!")
        else:
            log(f"Payment submission returned status {response.status_code}. Check your account.")

        return True

    log(f"No open '{config.CLASS_NAME}' classes found today.")
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
