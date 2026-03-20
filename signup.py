#!/usr/bin/env python3
"""
Tennis class signup script for wac.clubautomation.com.
Uses the by-date calendar view to find open "Pro on Duty" slots and register.
Checkout is completed via direct API call with a CapSolver-generated Turnstile token.
"""

import sys
import re  # used in get_cart_item_id
import datetime  # used in main() for timestamp
import time
import requests
import capsolver
import config
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

BASE_URL = "https://wac.clubautomation.com"

def log(msg):
    print(f"[tennis-signup] {msg}", flush=True)


def wait_for_page_load(driver):
    WebDriverWait(driver, config.TIMEOUT).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(1)


def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if config.CHROMIUM_PATH:
        options.binary_location = config.CHROMIUM_PATH
    if config.CHROMEDRIVER_PATH:
        from selenium.webdriver.chrome.service import Service
        return webdriver.Chrome(service=Service(config.CHROMEDRIVER_PATH), options=options)
    return webdriver.Chrome(options=options)


def login(driver):
    log("Logging in...")
    driver.get(BASE_URL)
    wait_for_page_load(driver)
    driver.find_element(By.NAME, "login").send_keys(config.USERNAME)
    driver.find_element(By.NAME, "password").send_keys(config.PASSWORD)
    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]').click()
    try:
        WebDriverWait(driver, config.TIMEOUT).until(lambda d: "/member" in d.current_url)
    except TimeoutException:
        pass
    wait_for_page_load(driver)
    time.sleep(2)

    errors = driver.find_elements(By.CSS_SELECTOR, ".error, .alert-danger")
    if errors:
        log(f"Login failed: {errors[0].text}")
        sys.exit(1)

    log(f"Logged in. URL: {driver.current_url}")


def load_by_date_view(driver):
    log("Navigating to Group Activities (by-date view)...")
    driver.find_element(By.XPATH, "//a[contains(text(), 'Group Activities')]").click()
    wait_for_page_load(driver)

    try:
        tab = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR,
                "#byDateTab, [data-tab='by-date'], a[href*='by-date']"))
        )
        tab.click()
        wait_for_page_load(driver)
        time.sleep(1)
        log(f"Switched to By Date view. URL: {driver.current_url}")
    except TimeoutException:
        log("By Date tab not found, may already be active.")


def add_to_cart(driver, title):
    """Select member and add to cart (Sign Up button already clicked). Returns True on success."""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".members-list"))
        )
    except TimeoutException:
        log("  Popup members list not found.")
        return False

    selected = driver.execute_script("""
        const getName = el => el.querySelector('span[id$="-name"]').textContent.trim();
        const already = document.querySelector('.select-member.registered');
        if (already) return getName(already);
        const member = document.querySelector('.select-member.approved');
        if (!member) return null;
        member.click();
        return getName(member);
    """)
    if not selected:
        log("  No approved member found in popup.")
        return False
    log(f"  Selected member: {selected}")
    time.sleep(0.5)

    driver.execute_script("document.querySelector('#add-to-cart').click()")

    try:
        WebDriverWait(driver, 8).until(lambda d: d.execute_script(
            "const el = document.querySelector('.view_cart_text'); "
            "return el && !el.innerText.includes('(0)');"
        ))
    except TimeoutException:
        log("  Cart did not update after clicking Add to Cart.")
        return False

    cart_text = driver.find_element(By.CSS_SELECTOR, ".view_cart_text").text
    log(f"  Cart updated: '{cart_text}'")
    return True


def get_cart_item_id(driver):
    """Navigate to cart page and extract the cart item ID from the page HTML."""
    driver.get(f"{BASE_URL}/member/cart")
    wait_for_page_load(driver)
    time.sleep(1)

    match = re.search(r'/cart_items/(\d+)/', driver.page_source)
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
        "type": "AntiTurnstileTaskProxyLess",
        "websiteURL": config.CF_TURNSTILE_URL,
        "websiteKey": config.CF_TURNSTILE_SITE_KEY,
    })
    token = solution.get("token")
    if token:
        log("  Turnstile solved.")
    else:
        log(f"  CapSolver returned unexpected response: {solution}")
    return token


def submit_payment(driver, cart_item_id, turnstile_token):
    """POST the payment directly using the session cookies from the browser."""
    cookies = {c["name"]: c["value"] for c in driver.get_cookies()}

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


def find_and_register(driver):
    if not config.SCHEDULES:
        log("No classes configured. Add classes via the web UI.")
        return False

    log("Searching for: " + ", ".join(s["class_name"] for s in config.SCHEDULES))

    try:
        WebDriverWait(driver, config.TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.block"))
        )
    except TimeoutException:
        log(f"No class entries found on page. URL: {driver.current_url}")
        return False

    all_blocks = driver.find_elements(By.CSS_SELECTOR, "div.block")
    open_blocks = [
        b for b in all_blocks
        if b.find_elements(By.CSS_SELECTOR, ".register_button:not(.register-button-closed)")
    ]
    log(f"Found {len(open_blocks)} class(es) with open registration.")

    for block in open_blocks:
        container_text = block.text.strip()

        matched_schedule = next(
            (s for s in config.SCHEDULES if s["class_name"].lower() in container_text.lower()),
            None
        )
        if not matched_schedule:
            continue

        title = ""
        for line in container_text.splitlines():
            line = line.strip()
            if matched_schedule["class_name"].lower() in line.lower():
                title = line
                break

        btn = block.find_element(By.CSS_SELECTOR, ".register_button:not(.register-button-closed)")
        btn_label = btn.text.strip() or "Sign Up"

        if "in cart" in btn_label.lower():
            log(f"  Skipping '{title}' — already in cart. Clear your cart at /member/cart first.")
            continue

        log(f"  Found open class: '{title}'")

        if config.DRY_RUN:
            log("  DRY RUN: Would register. Disable dry run via the web UI to sign up.")
            return True

        # Step 1: add to cart via popup
        driver.execute_script("arguments[0].scrollIntoView()", btn)
        driver.execute_script("arguments[0].click()", btn)
        if not add_to_cart(driver, title):
            continue

        # Step 2: get cart item ID
        cart_item_id = get_cart_item_id(driver)
        if not cart_item_id:
            continue

        # Step 3: solve Turnstile
        turnstile_token = solve_turnstile()
        if not turnstile_token:
            log("  Failed to get Turnstile token from CapSolver.")
            return False

        if config.CAPTCHA_TEST_ONLY:
            log("  CAPTCHA_TEST_ONLY: Turnstile solved successfully. Skipping payment submission.")
            log("  Clear your cart at /member/cart before running again.")
            return True

        # Step 4: submit payment directly via requests
        response = submit_payment(driver, cart_item_id, turnstile_token)

        if response.status_code == 200:
            log(f"Successfully registered for '{title}'!")
        else:
            log(f"Payment submission returned status {response.status_code}. Check your account.")

        return True

    log("No open classes found today.")
    return False


def main():
    log(datetime.datetime.now().strftime("Starting at %Y-%m-%d %H:%M:%S"))
    driver = make_driver()
    driver.implicitly_wait(config.TIMEOUT)

    try:
        login(driver)
        load_by_date_view(driver)
        find_and_register(driver)
    except Exception as e:
        log(f"Error: {e}")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
