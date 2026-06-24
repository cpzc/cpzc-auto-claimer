"""
CPZC Auto Claimer - Standalone GUI Application

A professional Tkinter GUI for the TikTok Username Auto-Claimer.
All scanning, claiming, and verification logic is built-in.

Requirements:
    pip install customtkinter selenium requests colorama
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, colorchooser
from colorama import Fore
import threading
import json
import os
import sys
import time
import re
import random
import string
import ctypes
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def load_config():
    config_path = os.path.join(SCRIPT_DIR, "config.json")
    defaults = {
        "discord_webhook_url": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "username_input_delay": 2,
        "headless": False,
    }
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults
    for k, v in defaults.items():
        config.setdefault(k, v)
    return config


def draw_border(text):
    lines = text.strip().split('\n')
    if not lines or not lines[0]:
        lines = [""]
    width = max(len(line) for line in lines) + 4
    print(Fore.CYAN + "╔" + "═" * width + "╗")
    for line in lines:
        print(Fore.CYAN + "║ " + Fore.WHITE + line.ljust(width - 2) + Fore.CYAN + " ║")
    print(Fore.CYAN + "╚" + "═" * width + "╝")


def random_alphanumeric(length):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_password(length=12):
    if length < 6: length = 6
    if length > 20: length = 20
    letters = string.ascii_letters
    digits = string.digits
    special = "!@#$%^&*"
    all_chars = letters + digits + special
    pw = [random.choice(letters), random.choice(digits), random.choice(special)]
    pw += [random.choice(all_chars) for _ in range(length - 3)]
    random.shuffle(pw)
    return ''.join(pw)


def select_combobox_value(driver, field_name, value_text):
    combobox = driver.find_element(By.XPATH, f"//div[@aria-label='{field_name}. Double-tap for more options']")
    driver.execute_script("arguments[0].scrollIntoView(true);", combobox)
    driver.execute_script("arguments[0].click();", combobox)
    time.sleep(0.3)
    option = driver.find_element(By.XPATH, f"//div[@role='option' and text()='{value_text}']")
    driver.execute_script("arguments[0].click();", option)
    time.sleep(0.2)


def save_account(filepath, email, password, created_username="", mail_pass="", birthday=""):
    header = "email,password,username,temp_mail_password,birthday\n"
    line = f"{email},{password},{created_username},{mail_pass},{birthday}\n"
    if not os.path.exists(filepath):
        with open(filepath, "w") as f:
            f.write(header)
            f.write(line)
    else:
        with open(filepath, "a") as f:
            f.write(line)


def check_rate_limited(driver):
    try:
        text = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "maximum number" in text or "try again later" in text
    except Exception:
        return False


def send_claim_notification(username, config):
    profile_url = f"https://www.tiktok.com/@{username}"
    message = f"🎉 Claimed @{username}!\n🔗 {profile_url}"
    webhook = config.get("discord_webhook_url", "").strip()
    if webhook:
        try:
            requests.post(webhook, json={"content": message}, timeout=10)
        except Exception:
            pass
    bot_token = config.get("telegram_bot_token", "").strip()
    chat_id = config.get("telegram_chat_id", "").strip()
    if bot_token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=10,
            )
        except Exception:
            pass


def send_captcha_notification(config, context=""):
    message = f"CAPTCHA requires manual solving!\n{context}\nPlease solve it in the browser."
    webhook = config.get("discord_webhook_url", "").strip()
    if webhook:
        try:
            resp = requests.post(webhook, json={"content": message}, timeout=10)
            print(Fore.GREEN + f"   Discord notification sent (HTTP {resp.status_code})")
        except Exception as e:
            print(Fore.RED + f"   Discord notification failed: {e}")
    else:
        print(Fore.YELLOW + "   No Discord webhook URL configured")
    bot_token = config.get("telegram_bot_token", "").strip()
    chat_id = config.get("telegram_chat_id", "").strip()
    if bot_token and chat_id:
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": message},
                timeout=10,
            )
            print(Fore.GREEN + f"   Telegram notification sent (HTTP {resp.status_code})")
        except Exception as e:
            print(Fore.RED + f"   Telegram notification failed: {e}")
    else:
        print(Fore.YELLOW + "   No Telegram bot token/chat ID configured")


def create_account(claim_driver=None, input_fn=None, pause_fn=None):
    if input_fn is None:
        input_fn = input
    if pause_fn is None:
        pause_fn = input

    own_driver = claim_driver is None
    if own_driver:
        opts = Options()
        chromium_path = r"C:\Program Files\Chromium\Application\chrome.exe"
        if os.path.exists(chromium_path):
            opts.binary_location = chromium_path
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--log-level=3")
        opts.add_argument("--start-minimized")
        driver = webdriver.Chrome(options=opts)
    else:
        driver = claim_driver

    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
                const origQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (p) => p.name === 'notifications'
                    ? Promise.resolve({ state: 'prompt' })
                    : origQuery(p);
            """
        })
    except Exception:
        pass

    wait = WebDriverWait(driver, 20)
    rngpassword = generate_password(12)
    auto_email = True
    url = 'https://www.tiktok.com/signup/phone-or-email/email'

    try:
        driver.get(url)
        time.sleep(2)

        try:
            lang_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[class*='SelectFormContainer']")))
            Select(lang_select).select_by_value("en")
        except Exception:
            pass
        time.sleep(0.3)

        select_combobox_value(driver, "Month", "January")
        select_combobox_value(driver, "Day", "1")
        select_combobox_value(driver, "Year", "2000")
        time.sleep(0.3)

        email_addr = ""
        email_pass = ""
        mail_token = ""
        try:
            domains_resp = requests.get("https://api.mail.tm/domains", timeout=10)
            domain = domains_resp.json()["hydra:member"][0]["domain"]
            local_part = "tiktok_" + random_alphanumeric(10).lower()
            email_addr = f"{local_part}@{domain}"
            email_pass = random_alphanumeric(20)
            requests.post("https://api.mail.tm/accounts", json={"address": email_addr, "password": email_pass}, timeout=10)
            token_resp = requests.post("https://api.mail.tm/token", json={"address": email_addr, "password": email_pass}, timeout=10)
            mail_token = token_resp.json()["token"]
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="email"]')))
            email_input.send_keys(email_addr)
        except Exception as e:
            auto_email = False
            email = input_fn("Enter your Email: ")
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="email"]')))
            email_input.send_keys(email)
            email_addr = email
        time.sleep(0.3)

        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(rngpassword)
        time.sleep(0.3)

        try:
            cb = driver.find_element(By.CSS_SELECTOR, 'input#email-consent')
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.2)
        except Exception:
            pass

        try:
            banner = driver.find_element(By.TAG_NAME, "tiktok-cookie-banner")
            driver.execute_script("arguments[0].remove();", banner)
        except Exception:
            pass

        for attempt in range(3):
            try:
                btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e="send-code-button"]')))
                driver.execute_script("arguments[0].click();", btn)
            except Exception:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                    driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    pass
            time.sleep(1.5)

            if auto_email:
                headers = {"Authorization": f"Bearer {mail_token}"}
                code_timeout = time.time() + 60
                get_code = None
                while time.time() < code_timeout:
                    try:
                        msg_resp = requests.get("https://api.mail.tm/messages", headers=headers, timeout=5)
                        msgs = msg_resp.json().get("hydra:member", [])
                        if msgs:
                            detail = requests.get(f"https://api.mail.tm/messages/{msgs[0]['id']}", headers=headers, timeout=5).json()
                            body = detail.get("text", "") or detail.get("html", "")
                            match = re.search(r'(\d{6})', body)
                            if match:
                                get_code = match.group(1)
                                break
                        time.sleep(3)
                    except Exception:
                        time.sleep(3)

                if get_code:
                    code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter 6-digit code"]')))
                    code_input.send_keys(get_code)
                    break
                else:
                    if attempt < 2:
                        driver.refresh()
                        time.sleep(2)
                        try:
                            lang_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[class*='SelectFormContainer']")))
                            Select(lang_select).select_by_value("en")
                        except Exception:
                            pass
                        time.sleep(0.3)
                        select_combobox_value(driver, "Month", "January")
                        select_combobox_value(driver, "Day", "1")
                        select_combobox_value(driver, "Year", "2000")
                        time.sleep(0.3)
                        if auto_email:
                            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="email"]')))
                            email_input.send_keys(email_addr)
                            driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(rngpassword)
                    else:
                        if own_driver:
                            driver.quit()
                        else:
                            pause_fn("Press Enter to return to login...")
                        return False
            else:
                code = input_fn("Enter Code from Email: ")
                code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter 6-digit code"]')))
                code_input.send_keys(code)
                break

        time.sleep(2)

        if check_rate_limited(driver):
            return False

        try:
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Next']")))
            next_btn.click()
            time.sleep(3)
        except Exception:
            pass

        if check_rate_limited(driver):
            return False

        birthday_str = "January 1, 2000"
        save_account(os.path.join(SCRIPT_DIR, "data", "created_accounts.csv"), email_addr, rngpassword, "", email_pass if auto_email else "", birthday_str)

        if own_driver:
            pause_fn("Press Enter to return...")

        return True
    except Exception as e:
        print(Fore.RED + f"Error: {e}")
        return False
    finally:
        if own_driver:
            driver.quit()


class TikTokSeleniumClaimer:
    def __init__(self, headless=False, check_interval=5, max_retries=3, username_input_delay=2):
        self.headless = headless
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.username_input_delay = float(username_input_delay)
        self.driver = None
        self.current_username = None
        self.claimed = False
        self.stop_scan = threading.Event()
        self.retry_counts = {}
        self.username_input = None
        self.edit_profile_modal_open = False
        self.username_input_selectors = [
            "input[placeholder*='sername']",
            "input[placeholder*='Username']",
            "input[name='uniqueId']",
            "input[name='username']",
            "//input[contains(@placeholder, 'sername')]",
            "//input[contains(@placeholder, 'Username')]",
            "//label[contains(text(), 'Username')]/..//input",
            "//div[contains(text(), 'Username')]/..//input",
        ]

    def setup_driver(self):
        """Initialize Chrome driver with Chromium/auto-detect Chrome"""
        print(Fore.CYAN + "\n🌐 Setting up browser...")

        chrome_options = Options()

        chromium_path = r"C:\Program Files\Chromium\Application\chrome.exe"
        if os.path.exists(chromium_path):
            chrome_options.binary_location = chromium_path
            print(Fore.WHITE + "   ✅ Found Chromium")
        else:
            print(Fore.WHITE + "   ℹ️ Using default Chrome (Chromium not found)")

        if self.headless:
            chrome_options.add_argument('--headless=new')
            print(Fore.WHITE + "   🕶️ Headless mode")
        else:
            print(Fore.WHITE + "   👁️ Visible mode")

        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--start-minimized')
        chrome_options.add_experimental_option("detach", True)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(15)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print(Fore.GREEN + "   ✅ Browser ready!")
            return True
        except Exception as e:
            print(Fore.RED + f"   ❌ Error: {e}")
            return False

    def login_with_cookies(self, cookies_file):
        """Load cookies from JSON file to login"""

        print(Fore.CYAN + "\n🔑 Loading session from cookies...")

        try:
            self.driver.get("https://www.tiktok.com")
            time.sleep(1)

            with open(cookies_file, 'r') as f:
                cookies = json.load(f)

            print(Fore.WHITE + f"   📦 {len(cookies)} cookies")

            for cookie in cookies:
                try:
                    cookie_dict = {
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie.get('domain', '.tiktok.com'),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                    }
                    if 'expirationDate' in cookie and cookie['expirationDate']:
                        cookie_dict['expiry'] = int(cookie['expirationDate'])
                    self.driver.add_cookie(cookie_dict)
                except Exception:
                    continue

            self.driver.refresh()
            time.sleep(1.5)

            print(Fore.GREEN + "   ✅ Cookies loaded!")
            return True

        except Exception as e:
            print(Fore.RED + f"   ❌ Error loading cookies: {e}")
            return False

    def login_with_credentials(self, credentials_file):
        """Login using email:password from a file (tries each account)"""
        print(Fore.CYAN + "\nLogging in with credentials...")

        try:
            with open(credentials_file, 'r') as f:
                lines = [l.strip() for l in f if ':' in l]
            if not lines:
                print(Fore.RED + "   No valid email:password entries found")
                return False
        except Exception as e:
            print(Fore.RED + f"   Error reading file: {e}")
            return False

        for entry in lines:
            email, password = entry.split(':', 1)
            print(Fore.WHITE + f"   Trying: {email}")
            try:
                self.driver.get("https://www.tiktok.com/login/phone-or-email/email")
                time.sleep(2)

                email_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="username"]'))
                )
                email_input.send_keys(email)
                self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(password)

                login_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e="login-button"]'))
                )
                login_btn.click()
                try:
                    WebDriverWait(self.driver, 10).until(
                        lambda d: "login" not in d.current_url.lower()
                    )
                except Exception:
                    pass

                if self.verify_logged_in():
                    print(Fore.GREEN + f"   ✅ Login successful: {email}")
                    return True
                print(Fore.YELLOW + f"   ❌ Failed: {email}")
            except Exception as e:
                print(Fore.YELLOW + f"   ❌ Error for {email}: {e}")

        print(Fore.RED + "   All accounts failed")
        return False

    def login_with_single_account(self, username, password, email=None, email_password=None, pause_fn=None, config=None):
        """Login with a single username:password pair. Handles verification codes if needed."""
        if pause_fn is None:
            pause_fn = input
        print(Fore.CYAN + f"\nLogging in as {username}...")
        try:
            self.driver.get("https://www.tiktok.com/login/phone-or-email/email")
            time.sleep(3)

            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="username"]'))
            )
            email_input.send_keys(username)
            time.sleep(0.3)
            self.driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(password)

            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-e2e="login-button"]'))
            )
            login_btn.click()
            time.sleep(5)

            page_source = self.driver.page_source.lower()
            page_url = self.driver.current_url.lower()
            body_text = ""
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            except Exception:
                pass

            is_verification = (
                "verify" in body_text or
                "really you" in body_text or
                "security" in body_text or
                "verification" in body_text or
                "send code" in body_text or
                "confirm" in body_text
            )
            is_login_page = "login" in page_url

            if is_verification and is_login_page:
                print(Fore.CYAN + "   🔐 Verification screen detected on login page")
                verification_handled = self._handle_login_verification(email, email_password, pause_fn, config=config)
                if verification_handled:
                    logged_in_user = self.get_current_username()
                    if logged_in_user and logged_in_user.lower() != username.lower():
                        print(Fore.RED + f"   ❌ Logged into wrong account: @{logged_in_user} (expected @{username})")
                        return False
                    if self.verify_logged_in():
                        print(Fore.GREEN + f"   ✅ Login successful (via verification): {username}")
                        return True
                print(Fore.YELLOW + f"   ❌ Verification did not complete login")
                return False

            if not is_login_page:
                logged_in_user = self.get_current_username()
                if logged_in_user and logged_in_user.lower() != username.lower():
                    print(Fore.RED + f"   ❌ Logged into wrong account: @{logged_in_user} (expected @{username})")
                    return False
                if self.verify_logged_in():
                    print(Fore.GREEN + f"   ✅ Login successful: {username}")
                    return True

            print(Fore.YELLOW + f"   ❌ Failed: {username}")
            return False
        except Exception as e:
            print(Fore.YELLOW + f"   ❌ Error: {e}")
            return False

    def _handle_login_verification(self, email=None, email_password=None, pause_fn=None, config=None):
        if pause_fn is None:
            pause_fn = input
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "verify" not in body_text.lower() and "really you" not in body_text.lower():
                return False

            print(Fore.CYAN + "   🔐 Verification required - 'Verify it's really you' detected")

            email_option_selectors = [
                '//div[contains(@class, "pc-home-item")]',
                '//div[contains(@class, "home-item")]',
                '//div[contains(@data-testid, "email")]',
                '//div[contains(., "Email") and contains(., "@")]',
                '//div[contains(@class, "item")]//div[contains(text(), "@")]',
            ]
            email_option = None
            for sel in email_option_selectors:
                try:
                    options = self.driver.find_elements(By.XPATH, sel)
                    for opt in options:
                        opt_text = opt.text.lower()
                        if "@" in opt_text or "email" in opt_text:
                            if opt.is_displayed():
                                email_option = opt
                                break
                    if email_option:
                        break
                except Exception:
                    continue

            if not email_option:
                try:
                    all_divs = self.driver.find_elements(By.TAG_NAME, "div")
                    for div in all_divs:
                        try:
                            div_text = div.text.strip()
                            if "@" in div_text and ("@" in div_text) and div.is_displayed():
                                classes = div.get_attribute("class") or ""
                                if "item" in classes.lower() or "home" in classes.lower():
                                    email_option = div
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

            if email_option:
                print(Fore.CYAN + f"   📩 Clicking email option: {email_option.text[:50]}...")
                try:
                    email_option.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", email_option)
                time.sleep(5)

                has_captcha = False
                try:
                    has_captcha = self.driver.execute_script("""
                        var iframes = document.querySelectorAll('iframe');
                        for (var i = 0; i < iframes.length; i++) {
                            var src = (iframes[i].src || '').toLowerCase();
                            if (src.includes('captcha') || src.includes('challenge') || src.includes('slider') || src.includes('verify') || src.includes('geetest') || src.includes('dk')) {
                                return true;
                            }
                        }
                        var captchaEls = document.querySelectorAll('[class*="captcha"], [class*="challenge"], [id*="captcha"], [class*="slider"], [class*="secsdk"], [class*="geetest"], [class*="captcha_verify"], [id*="captcha_"], [class*="secsdk-captcha"]');
                        for (var j = 0; j < captchaEls.length; j++) {
                            if (captchaEls[j].offsetParent !== null) return true;
                        }
                        var allText = document.body.innerText.toLowerCase();
                        if (allText.includes('drag the slider') || allText.includes('slide to verify') || allText.includes('verify you are human')) {
                            return true;
                        }
                        return false;
                    """)
                except Exception as e:
                    print(Fore.RED + f"   CAPTCHA detection error: {e}")

                if has_captcha:
                    print(Fore.YELLOW + "   CAPTCHA detected - please solve the slider puzzle in the browser")
                    if config:
                        send_captcha_notification(config, "Account login verification for TikTok")
                    pause_fn(Fore.YELLOW + "   Solve the CAPTCHA puzzle in the browser, then press Enter here to continue...")
                    time.sleep(2)
                else:
                    print(Fore.CYAN + "   No CAPTCHA, waiting for email to arrive...")
                    time.sleep(3)
            else:
                print(Fore.YELLOW + "   No email option card found, code may already be sent or page layout differs")

            max_retries = 3
            for attempt in range(max_retries):
                code = None
                if email and email_password:
                    code = self._get_code_from_inbox(email, email_password, pause_fn)
                else:
                    if attempt == 0:
                        print(Fore.YELLOW + "\n   ⚠️  No email credentials for this account.")
                        pause_fn(Fore.YELLOW + "   A verification code was sent to the account's email. Solve CAPTCHA in browser if needed, then press Enter...")
                    code = input(Fore.CYAN + "   Enter the 6-digit verification code: ").strip()

                if not code:
                    print(Fore.RED + "   ❌ No verification code obtained")
                    return False

                print(Fore.CYAN + f"   Entering code: {code} (attempt {attempt+1}/{max_retries})")
                time.sleep(2)

                code_input = None
                code_input_selectors = [
                    'input[data-e2e="verify-code-input"]',
                    'input[maxlength="6"]',
                    'input[name="verify_code"]',
                    'input[name="code"]',
                    'input[placeholder*="code"]',
                    'input[placeholder*="Code"]',
                    'input[type="tel"]',
                    'input[type="number"]',
                    'input[type="text"]',
                ]
                for sel in code_input_selectors:
                    try:
                        candidates = self.driver.find_elements(By.CSS_SELECTOR, sel)
                        for c in candidates:
                            if c.is_displayed():
                                code_input = c
                                break
                        if code_input:
                            break
                    except Exception:
                        continue

                if not code_input:
                    try:
                        inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        for inp in inputs:
                            try:
                                ml = inp.get_attribute("maxlength")
                                if ml and int(ml) <= 8 and inp.is_displayed():
                                    code_input = inp
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                if code_input:
                    try:
                        code_input.click()
                        time.sleep(0.5)
                        self.driver.execute_script("""
                            var input = arguments[0];
                            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                            nativeInputValueSetter.call(input, arguments[1]);
                            input.dispatchEvent(new Event('input', {bubbles: true}));
                            input.dispatchEvent(new Event('change', {bubbles: true}));
                            input.dispatchEvent(new KeyboardEvent('keydown', {bubbles: true}));
                            input.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
                            input.dispatchEvent(new Event('blur', {bubbles: true}));
                            input.dispatchEvent(new Event('focus', {bubbles: true}));
                        """, code_input, code)
                        time.sleep(1)
                        entered_val = code_input.get_attribute("value")
                        print(Fore.CYAN + f"   Input value after JS set: '{entered_val}'")
                        if not entered_val or entered_val != code:
                            print(Fore.YELLOW + "   JS set didn't stick, trying send_keys approach...")
                            code_input.click()
                            time.sleep(0.3)
                            code_input.clear()
                            time.sleep(0.3)
                            for ch in code:
                                code_input.send_keys(ch)
                                time.sleep(0.1)
                            time.sleep(1)
                            entered_val = code_input.get_attribute("value")
                            print(Fore.CYAN + f"   Input value after send_keys: '{entered_val}'")
                    except Exception as e:
                        print(Fore.YELLOW + f"   Code entry error: {e}")
                        try:
                            code_input.send_keys(code)
                            time.sleep(1)
                        except Exception:
                            pass
                    time.sleep(1)
                else:
                    print(Fore.RED + "   ❌ Could not find verification code input field")
                    return False

                print(Fore.CYAN + "   Submitting verification code...")
                time.sleep(2)

                print(Fore.CYAN + "   Waiting for 'Next' button to become enabled...")
                next_btn = None
                for wait in range(10):
                    try:
                        all_btns = self.driver.find_elements(By.CSS_SELECTOR, 'button')
                        for b in all_btns:
                            try:
                                if b.text.strip().lower() == "next" and b.is_displayed():
                                    next_btn = b
                                    break
                            except Exception:
                                continue
                        if next_btn:
                            is_disabled = next_btn.get_attribute("disabled")
                            if is_disabled is None:
                                print(Fore.GREEN + f"   ✅ Next button enabled (attempt {wait+1})")
                                break
                            else:
                                print(Fore.YELLOW + f"   Next button still disabled, waiting... ({wait+1}/10)")
                    except Exception:
                        pass
                    time.sleep(1)

                submit_success = False
                if next_btn:
                    try:
                        is_disabled = next_btn.get_attribute("disabled")
                        if is_disabled is not None:
                            print(Fore.YELLOW + "   Button still disabled, forcing click via JS...")
                            self.driver.execute_script("arguments[0].disabled = false; arguments[0].click();", next_btn)
                            submit_success = True
                        else:
                            next_btn.click()
                            submit_success = True
                    except Exception:
                        self.driver.execute_script("arguments[0].disabled = false; arguments[0].click();", next_btn)
                        submit_success = True

                if not submit_success:
                    try:
                        self.driver.execute_script("""
                            var btns = document.querySelectorAll('button');
                            for (var i = 0; i < btns.length; i++) {
                                var t = btns[i].textContent.toLowerCase().trim();
                                if (t.includes('next') || t.includes('log in') || t.includes('verify') || t.includes('submit') || btns[i].type === 'submit') {
                                    btns[i].disabled = false;
                                    btns[i].click();
                                    break;
                                }
                            }
                        """)
                        submit_success = True
                    except Exception:
                        pass

                if not submit_success:
                    try:
                        code_input.submit()
                    except Exception:
                        pass

                time.sleep(3)

                post_captcha = False
                try:
                    post_captcha = self.driver.execute_script("""
                        var iframes = document.querySelectorAll('iframe');
                        for (var i = 0; i < iframes.length; i++) {
                            var src = (iframes[i].src || '').toLowerCase();
                            if (src.includes('captcha') || src.includes('challenge') || src.includes('slider') || src.includes('verify') || src.includes('geetest') || src.includes('dk')) {
                                return true;
                            }
                        }
                        var captchaEls = document.querySelectorAll('[class*="captcha"], [class*="challenge"], [id*="captcha"], [class*="slider"], [class*="secsdk"], [class*="geetest"], [class*="captcha_verify"], [id*="captcha_"], [class*="secsdk-captcha"]');
                        for (var j = 0; j < captchaEls.length; j++) {
                            if (captchaEls[j].offsetParent !== null) return true;
                        }
                        var allText = document.body.innerText.toLowerCase();
                        if (allText.includes('drag the slider') || allText.includes('slide to verify') || allText.includes('verify you are human')) {
                            return true;
                        }
                        return false;
                    """)
                except Exception as e:
                    print(Fore.RED + f"   Post-code CAPTCHA detection error: {e}")

                if post_captcha:
                    print(Fore.YELLOW + "   CAPTCHA appeared after code submission - please solve the slider puzzle")
                    if config:
                        send_captcha_notification(config, "Post-code CAPTCHA for TikTok verification")
                    pause_fn(Fore.YELLOW + "   Solve the CAPTCHA in the browser, then press Enter here to continue...")
                    time.sleep(3)

                time.sleep(2)

                page_text = ""
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                except Exception:
                    pass

                if "expired" in page_text or "incorrect" in page_text:
                    print(Fore.YELLOW + f"   ⚠️  Code expired or incorrect — fetching new code from inbox...")
                    time.sleep(3)
                    continue

                if self.verify_logged_in():
                    return True

                still_on_verification = "verify" in page_text or "really you" in page_text
                if still_on_verification:
                    print(Fore.YELLOW + f"   ⚠️  Still on verification page — retrying with new code...")
                    time.sleep(3)
                    continue

                print(Fore.YELLOW + "   Page changed, checking login status...")
                if self.verify_logged_in():
                    return True

                print(Fore.RED + "   ❌ Unexpected page state after code submission")
                return False

            print(Fore.RED + f"   ❌ All {max_retries} attempts failed")
            return False

        except Exception as e:
            print(Fore.YELLOW + f"   ⚠️  Verification handling error: {e}")
            return False

    def _dismiss_cookie_banner(self):
        try:
            self.driver.execute_script("""
                var acceptBtns = document.querySelectorAll('button, a, div');
                for (var i = 0; i < acceptBtns.length; i++) {
                    var t = acceptBtns[i].textContent.toLowerCase().trim();
                    if (t === 'accept' || t === 'accept all' || t === 'accept cookies' || t === 'agree' || t === 'got it' || t === 'ok') {
                        acceptBtns[i].click();
                        break;
                    }
                }
            """)
            time.sleep(1)
        except Exception:
            pass

    @staticmethod
    def _is_firstmail_email(email):
        if not email or "@" not in email:
            return False
        domain = email.split("@")[-1].lower()
        return domain in (
            "firstmail.ltd", "firstmail.online",
            "firstmailler.com", "firstmailler.net",
            "raymanmail.com", "fmaild.com", "dfirstmail.com",
            "tformemail.com", "mergencmail.com", "protecemail.com",
            "ervmail.com", "espismail.com", "spitalitmail.com",
            "maillsk.com", "maillv.com", "oonmail.com", "znemail.com",
            "sabesmail.com", "bonjourfmail.com", "reevalmail.com", "bientotmail.com",
        )

    def _fill_firstmail_credentials(self, email, email_password):
        self.driver.execute_script("""
            var emailInput = document.getElementById('email-desktop') || document.querySelector('input[name="email"]');
            var passInput = document.getElementById('password-desktop') || document.querySelector('input[type="password"]');
            if (emailInput) {
                emailInput.value = arguments[0];
                emailInput.dispatchEvent(new Event('input', {bubbles: true}));
                emailInput.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (passInput) {
                passInput.value = arguments[1];
                passInput.dispatchEvent(new Event('input', {bubbles: true}));
                passInput.dispatchEvent(new Event('change', {bubbles: true}));
            }
        """, email, email_password)
        time.sleep(0.5)

        self.driver.execute_script("""
            var form = document.getElementById('login-form-desktop') || document.getElementById('login-form-mobile') || document.querySelector('form[method="post"]');
            if (form) { form.submit(); }
        """)
        time.sleep(5)

    def _search_for_code(self):
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            codes_found = re.findall(r'\b\d{6}\b', body_text)
            if codes_found:
                return codes_found[0]
        except Exception:
            pass
        return None

    def _get_code_from_inbox(self, email, email_password, pause_fn=None):
        if pause_fn is None:
            pause_fn = input
        if not self._is_firstmail_email(email):
            print(Fore.RED + f"   Only FirstMail emails can be used for inbox (got: {email})")
            return None
        print(Fore.CYAN + "   📧 Opening FirstMail inbox in new tab...")
        original_window = self.driver.current_window_handle

        try:
            self.driver.execute_script("window.open('https://firstmail.ltd/ru-RU/webmail/login', '_blank');")
            time.sleep(1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(3)

            self._dismiss_cookie_banner()
            pause_fn(Fore.YELLOW + "\n   Solve the CAPTCHA on the FirstMail tab if needed, then press Enter here to continue...")
            self._fill_firstmail_credentials(email, email_password)

            print(Fore.CYAN + "   Looking for TikTok verification email...")
            code = None
            for attempt in range(5):
                try:
                    code = self._search_for_code()
                    if code:
                        print(Fore.GREEN + f"   ✅ Found verification code: {code}")
                        return code

                    email_rows = self.driver.find_elements(By.CSS_SELECTOR, 'tr, [class*="message"], [class*="mail-item"], [class*="email"]')
                    for row in email_rows:
                        try:
                            row_text = row.text.lower()
                            if "tiktok" in row_text or "verification" in row_text or "verify" in row_text:
                                print(Fore.CYAN + f"   Found TikTok email: {row.text[:60]}...")
                                row.click()
                                time.sleep(3)
                                email_body = self.driver.find_element(By.TAG_NAME, "body").text
                                codes_found = re.findall(r'\b\d{6}\b', email_body)
                                if codes_found:
                                    code = codes_found[0]
                                    print(Fore.GREEN + f"   ✅ Extracted verification code: {code}")
                                    return code
                        except Exception:
                            continue

                    print(Fore.YELLOW + f"   Attempt {attempt+1}/5: Waiting for email to arrive...")
                    time.sleep(5)
                    try:
                        refresh_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[class*="refresh"], a[class*="refresh"], [data-action="refresh"]')
                        refresh_btn.click()
                    except Exception:
                        self.driver.refresh()
                    time.sleep(3)

                except Exception as e:
                    print(Fore.YELLOW + f"   Attempt {attempt+1}/5: Error searching emails: {e}")
                    time.sleep(5)

            return None

        except Exception as e:
            print(Fore.RED + f"   ❌ Error accessing inbox: {e}")
            return None
        finally:
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except Exception:
                try:
                    self.driver.switch_to.window(original_window)
                except Exception:
                    pass

    def open_inbox(self, email, email_password, pause_fn=None):
        if pause_fn is None:
            pause_fn = input
        if not self._is_firstmail_email(email):
            print(Fore.RED + f"   Only FirstMail emails can be used for inbox (got: {email})")
            return False
        print(Fore.CYAN + "\nOpening FirstMail webmail...")
        try:
            self.driver.get("https://firstmail.ltd/ru-RU/webmail/login")
            time.sleep(3)

            self._dismiss_cookie_banner()
            pause_fn(Fore.YELLOW + "\nSolve the CAPTCHA in the browser, then press Enter to continue...")
            self._fill_firstmail_credentials(email, email_password)

            print(Fore.GREEN + "   ✅ Inbox login submitted")
            return True
        except Exception as e:
            print(Fore.RED + f"   ❌ Inbox login error: {e}")
            return False

    def save_cookies(self, filepath):
        try:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(Fore.GREEN + f"   ✅ Cookies saved ({len(cookies)})")
            return True
        except Exception as e:
            print(Fore.RED + f"   ❌ Failed to save cookies: {e}")
            return False

    def manual_login(self, pause_fn=None):
        if pause_fn is None:
            pause_fn = input
        print(Fore.CYAN + "\n🔐 Manual Login Required")
        print(Fore.CYAN + "="*60)
        print(Fore.WHITE + "Please login to TikTok in the browser window that opened.")
        print("  • QR Code")
        print("  • Phone/Email/Username")
        print("  • Social media accounts")
        print(Fore.YELLOW + "\nOnce logged in, press Enter here to continue...")
        print(Fore.CYAN + "="*60)

        try:
            self.driver.get("https://www.tiktok.com/login")
            pause_fn(Fore.WHITE + "\n⏸️  Press Enter after you've logged in: ")
            time.sleep(1)
            return self.verify_logged_in()

        except Exception as e:
            print(Fore.RED + f"❌ Error during manual login: {e}")
            return False

    def verify_logged_in(self):
        try:
            time.sleep(1)
            current_url = self.driver.current_url.lower()
            if "login" not in current_url:
                return True

            try:
                self.driver.set_page_load_timeout(10)
                self.driver.get("https://www.tiktok.com/setting")
                time.sleep(1.5)
                if "login" not in self.driver.current_url.lower():
                    page = self.driver.page_source
                    if "uniqueId" in page or "Edit profile" in page:
                        return True
            except Exception:
                pass
            finally:
                self.driver.set_page_load_timeout(15)

            return False

        except Exception:
            return False

    def get_current_username(self):
        print(Fore.CYAN + "\n📋 Fetching current username...")

        try:
            self.driver.get("https://www.tiktok.com/setting")
            time.sleep(1.5)

            page_source = self.driver.page_source

            patterns = [
                r'"uniqueId"\s*:\s*"([a-zA-Z0-9_\.]{2,})"',
                r'@([a-zA-Z0-9_\.]{2,})',
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    valid = [m for m in matches if m.lower() not in ['tiktok', 'user', 'profile', 'settings']]
                    if valid:
                        username = max(valid, key=len).lower()
                        print(Fore.GREEN + f"   ✅ @{username}")
                        return username

            try:
                username_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text'][placeholder*='sername']")
                username = username_input.get_attribute('value')
                if username:
                    print(Fore.GREEN + f"   ✅ @{username}")
                    return username.lower()
            except Exception:
                pass

            print(Fore.YELLOW + "   ⚠️ Could not detect username")
            return None

        except Exception as e:
            print(Fore.RED + f"   ❌ Error: {e}")
            return None

    def check_username_availability(self, username):
        print(f"\n🔍 Checking if @{username} is available...")

        try:
            self.driver.get(f"https://www.tiktok.com/@{username}")
            time.sleep(1)

            page_source = self.driver.page_source.lower()

            not_found_indicators = [
                "couldn't find this account",
                "account not found",
                "page not available",
                "this account doesn't exist",
            ]

            for indicator in not_found_indicators:
                if indicator in page_source:
                    print(f"   ✅ Username appears to be available!")
                    return True, "Available"

            if "video" in page_source or "followers" in page_source:
                print(f"   ❌ Username is taken")
                return False, "Username is already taken"

            print(f"   ⚠️ Status unclear - attempting claim anyway")
            return True, "Status uncertain"

        except Exception as e:
            print(f"   ⚠️ Error checking: {e}")
            return True, "Check failed - attempting claim"

    def has_ready_username_input(self):
        try:
            return (
                self.edit_profile_modal_open
                and self.username_input is not None
                and self.username_input.is_displayed()
                and self.username_input.is_enabled()
            )
        except (StaleElementReferenceException, WebDriverException):
            self.username_input = None
            self.edit_profile_modal_open = False
            return False

    def find_username_input(self, timeout=3):
        for selector in self.username_input_selectors:
            try:
                if selector.startswith('//'):
                    username_input = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    username_input = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )

                if username_input and username_input.is_displayed() and username_input.is_enabled():
                    self.username_input = username_input
                    self.edit_profile_modal_open = True
                    print("   Username input field is ready")
                    return username_input
            except Exception:
                continue

        self.username_input = None
        self.edit_profile_modal_open = False
        return None

    def initialize_edit_profile_setup(self):
        print(Fore.CYAN + "\n" + "="*60)
        print(Fore.WHITE + "Initial setup: opening Edit Profile once")
        print(Fore.CYAN + "="*60)

        if not self.verify_logged_in():
            return False

        detected_username = self.get_current_username()
        if not detected_username:
            print(Fore.YELLOW + "   ⚠️ Could not detect username")
            return False

        if self.current_username and detected_username != self.current_username:
            print(Fore.RED + f"   ❌ Account mismatch: @{detected_username} (expected @{self.current_username})")
            return False

        self.current_username = detected_username
        print(Fore.GREEN + f"   ✅ @{self.current_username}")

        if not self.navigate_to_edit_profile():
            return False

        return self.has_ready_username_input()

    def navigate_to_edit_profile(self):
        if self.has_ready_username_input():
            return True

        print(Fore.CYAN + "\n📍 Initializing profile navigation...")
        self.edit_profile_modal_open = False

        try:
            if not self.current_username:
                print(Fore.WHITE + "   🔍 Getting current username...")
                self.current_username = self.get_current_username()
                if not self.current_username:
                    print(Fore.YELLOW + "   ⚠️ Could not get username, going to main page")
                    self.driver.get("https://www.tiktok.com")
                    time.sleep(1.5)

            if self.current_username:
                profile_url = f"https://www.tiktok.com/@{self.current_username}"
                print(Fore.WHITE + f"   🔗 {profile_url}")
                self.driver.get(profile_url)
                time.sleep(1.5)
            else:
                self.driver.get("https://www.tiktok.com")
                time.sleep(1.5)

            print(Fore.WHITE + "   🔍 Looking for Edit profile...")

            edit_button_selectors = [
                "button[data-e2e='edit-profile-entrance']",
                "//button[@data-e2e='edit-profile-entrance']",
                "//button[contains(@class, 'TUXButton') and contains(., 'Edit profile')]",
                "button[aria-haspopup='dialog'][aria-expanded='false']",
                "//button[contains(text(), 'Edit profile')]",
                "//a[contains(text(), 'Edit profile')]",
            ]

            edit_button = None
            for selector in edit_button_selectors:
                try:
                    if selector.startswith('//'):
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    if edit_button:
                        break
                except Exception:
                    continue

            if not edit_button:
                print(Fore.YELLOW + "   ⚠️ Could not find Edit profile button")
                return False

            print(Fore.WHITE + "   🖱️ Clicking Edit profile...")
            edit_button.click()
            time.sleep(1)

            if not self.find_username_input(timeout=5):
                print(Fore.YELLOW + "   ⚠️ Username input not found after opening modal")
                return False

            print(Fore.GREEN + "   ✅ Edit profile modal opened!")
            return True

        except Exception as e:
            print(Fore.RED + f"   ❌ Error navigating: {e}")
            return False

    def claim_username(self, username, skip_availability_check=False, quiet=False):
        username = username.replace('@', '').strip().lower()

        if not quiet:
            print(Fore.CYAN + f"\n{'='*60}")
            print(Fore.WHITE + f"🎯 Claiming: @{username}")
            print(Fore.CYAN + f"{'='*60}")

        if self.current_username == username:
            return True, f"Already using @{username}"

        if not skip_availability_check:
            available, msg = self.check_username_availability(username)
            if not available:
                return False, msg

        if not self.has_ready_username_input():
            if not self.navigate_to_edit_profile():
                return False, "Failed to restore edit profile"

        try:
            inp = self.username_input
            if not inp:
                return False, "Username input not found"

            inp.click()
            time.sleep(0.3)
            inp.send_keys(Keys.CONTROL + "a")
            time.sleep(0.1)
            inp.send_keys(Keys.DELETE)
            time.sleep(0.3)

            self.driver.execute_script("""
                var inp = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(inp, arguments[1]);
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                inp.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                inp.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                inp.dispatchEvent(new Event('blur', { bubbles: true }));
                inp.dispatchEvent(new Event('focus', { bubbles: true }));
            """, inp, username)
            time.sleep(0.5)

            entered_val = inp.get_attribute("value")
            if not entered_val or entered_val != username:
                inp.click()
                time.sleep(0.3)
                inp.send_keys(Keys.CONTROL + "a")
                time.sleep(0.1)
                inp.send_keys(Keys.DELETE)
                time.sleep(0.3)
                for ch in username:
                    inp.send_keys(ch)
                    time.sleep(0.05)
                time.sleep(0.5)

            if not quiet:
                print(Fore.WHITE + f"⏳ Waiting {self.username_input_delay}s for validation...")
            time.sleep(self.username_input_delay)

            if not quiet:
                print(Fore.WHITE + "🔍 Looking for Save button...")
            save = None
            for sel in [
                "//button[contains(text(), 'Save')]",
                "button[type='submit']",
                "//button[contains(@class, 'save')]",
            ]:
                try:
                    if sel.startswith('//'):
                        save = self.driver.find_element(By.XPATH, sel)
                    else:
                        save = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if save and save.is_displayed() and save.is_enabled():
                        break
                    save = None
                except Exception:
                    continue

            if not save:
                return False, "Username not available"

            if not quiet:
                print(Fore.WHITE + "🖱️ Clicking Save...")
            save.click()
            time.sleep(1.5)

            if "30 days" in self.driver.page_source.lower():
                for sel in ["//button[contains(text(), 'Confirm')]", "button[data-e2e='confirm']"]:
                    try:
                        btn = self.driver.find_element(By.XPATH, sel) if sel.startswith('//') else self.driver.find_element(By.CSS_SELECTOR, sel)
                        if btn and btn.is_displayed():
                            btn.click()
                            time.sleep(2)
                            break
                    except Exception:
                        continue

            new = self.get_current_username()
            if new == username:
                self.current_username = username
                return True, f"Successfully claimed @{username}!"

            try:
                modal = self.driver.find_element(By.CSS_SELECTOR, "div[role='dialog']")
                if "auto-moderat" in modal.text.lower():
                    self.driver.find_element(By.CSS_SELECTOR, "button[aria-label='Close']").click()
                    return False, "Auto-moderated by TikTok"
            except Exception:
                pass

            return False, "Claim failed"

        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    def check_username_threaded(self, username, session):
        endpoint = "https://www.tiktok.com/@"
        try:
            request = session.get(endpoint + username, timeout=(3, 5))
            if request.status_code == 404:
                return username, True
            if request.status_code == 200:
                text = request.text.lower()
                if any(kw in text for kw in ["followingcount", "followercount", "video__ns"]):
                    return username, False
                else:
                    return username, True
            else:
                return username, None
        except Exception:
            return username, None

    def auto_scan_and_claim_mode(self, usernames_file, config=None, threads=None):
        print("\n" + "="*60)
        print("🔍 Auto Scan & Claim Mode")
        print("="*60)
        print(f"📁 Reading usernames from: {usernames_file}")
        print("💡 Checking via HTTP requests + threading (checker.py method)")
        print("🛑 Press Ctrl+C to stop\n")

        usernames = []
        try:
            with open(usernames_file, 'r') as f:
                for line in f:
                    u = line.strip().lower().replace('@', '')
                    if u and u.replace('_', '').replace('.', '').isalnum():
                        usernames.append(u)
        except FileNotFoundError:
            print(f"❌ File not found: {usernames_file}")
            return

        if not usernames:
            print("❌ No valid usernames found in file")
            return

        print(f"📊 Loaded {len(usernames)} usernames\n")

        self.claimed = False
        self.stop_scan.clear()

        if threads is None:
            threads_prompt = (
                "   WORKER THREADS   \n"
                "--------------------\n"
                " How many parallel checks?\n"
                " (1-20, default 5)"
            )
            draw_border(threads_prompt)
            try:
                threads = int(input(f"{Fore.YELLOW}>> {Fore.WHITE}") or "5")
            except ValueError:
                threads = 5
        threads = max(1, min(20, threads))

        script_dir = os.path.dirname(os.path.abspath(__file__))
        claim_log = os.path.join(script_dir, "output", "claimed.txt")
        error_log = os.path.join(script_dir, "output", "errors.log")
        os.makedirs(os.path.join(script_dir, "output"), exist_ok=True)

        lock = threading.RLock()
        claiming_event = threading.Event()
        claiming_event.set()
        checked = 0
        total = len(usernames)
        error_cooldown = 0.0
        thread_local = threading.local()

        def get_session():
            if not hasattr(thread_local, 'session'):
                thread_local.session = requests.Session()
                thread_local.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
            return thread_local.session

        def safe_print(*args, **kwargs):
            with lock:
                print(*args, **kwargs, flush=True)

        def update_title():
            title = f"Checking {checked}/{total} | {'CLAIMED' if self.claimed else 'Scanning'}"
            try:
                ctypes.windll.kernel32.SetConsoleTitleW(title)
            except Exception:
                pass

        def wait_cooldown():
            nonlocal error_cooldown
            deadline = time.time() + 60
            while time.time() < deadline:
                with lock:
                    remaining = error_cooldown - time.time()
                    if remaining <= 0:
                        break
                time.sleep(0.5)

        def check_and_claim(username):
            nonlocal checked, error_cooldown
            if self.claimed or self.stop_scan.is_set():
                return

            wait_cooldown()

            time.sleep(0.3)

            result = self.check_username_threaded(username, get_session())

            with lock:
                checked += 1
                current = checked
            update_title()

            _, available = result

            if available is True:
                with lock:
                    if self.claimed or not claiming_event.is_set():
                        return
                    claiming_event.clear()
                safe_print(f"  ✅ [{current}/{total}] @{username} — AVAILABLE, claiming...")
                try:
                    success, msg = self.claim_username(username, skip_availability_check=True, quiet=True)
                except Exception as e:
                    success, msg = False, f"Claim crashed: {e}"
                safe_print(f"     🎉 Claimed @{username}!" if success else f"     ⏭️ {msg}")
                if success:
                    safe_print(f"     🔗 https://www.tiktok.com/@{username}")
                    self.claimed = True
                    update_title()
                    try:
                        with open(claim_log, 'a') as f:
                            f.write(f"{datetime.now().isoformat()} @{username}\n")
                    except Exception:
                        pass
                    if config:
                        send_claim_notification(username, config)
                claiming_event.set()
            elif available is False:
                safe_print(f"  ❌ [{current}/{total}] @{username}")
            else:
                with lock:
                    wait_secs = min(15, max(3, checked // 20 * 2))
                    error_cooldown = time.time() + wait_secs
                    safe_print(f"  ⚠️ [{current}/{total}] @{username} — error (waiting {wait_secs}s)")
                    try:
                        with open(error_log, 'a') as f:
                            f.write(f"{datetime.now().isoformat()} @{username} (entry {current})\n")
                    except Exception:
                        pass

        worker_threads = []
        stop_workers = threading.Event()
        username_iter = iter(usernames)
        iter_lock = threading.Lock()
        print(Fore.GREEN + f"   Starting {threads} workers...", flush=True)

        test_session = requests.Session()
        test_session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
        try:
            test_resp = test_session.get("https://www.tiktok.com/@tiktok", timeout=10)
            print(Fore.GREEN + f"   ✅ TikTok reachable (status {test_resp.status_code})", flush=True)
        except Exception as e:
            print(Fore.RED + f"   ❌ TikTok unreachable: {e}", flush=True)

        def worker_loop(worker_id):
            safe_print(Fore.CYAN + f"   Worker {worker_id} started")
            while not self.claimed and not self.stop_scan.is_set() and not stop_workers.is_set():
                with iter_lock:
                    try:
                        username = next(username_iter)
                    except StopIteration:
                        return
                try:
                    check_and_claim(username)
                except Exception as e:
                    safe_print(Fore.RED + f"  ⚠️ Worker error: {e}")

        for i in range(threads):
            t = threading.Thread(target=worker_loop, args=(i+1,))
            t.daemon = True
            t.start()
            worker_threads.append(t)

        try:
            last_progress = time.time()
            last_checked = 0
            while any(t.is_alive() for t in worker_threads):
                time.sleep(1)
                with lock:
                    if time.time() - last_progress > 60 and checked == last_checked:
                        safe_print(Fore.RED + "\n  ⚠️ No progress for 60s — stopping workers")
                        stop_workers.set()
                        break
                    last_progress = time.time() if checked != last_checked else last_progress
                    last_checked = checked
        except KeyboardInterrupt:
            print("\n\n👋 Stopped by user")
            stop_workers.set()
            time.sleep(1)

        if not self.claimed:
            print(f"\n{'='*60}")
            print("📊 Scan complete - no available usernames claimed")
            print(f"{'='*60}")

    def cleanup(self):
        if self.driver:
            print("\n🧹 Cleaning up...")
            try:
                self.driver.quit()
                print("   ✅ Browser closed")
            except Exception:
                pass


THEME_PRESETS = {
    "Midnight": {
        "bg": "#0f0f0f", "card": "#1a1a2e", "card_hover": "#1f1f3a",
        "accent": "#00d4ff", "accent_dim": "#0099cc",
        "success": "#00e676", "error": "#ff5252", "warning": "#ffab40",
        "text": "#e0e0e0", "text_dim": "#808080",
        "sidebar": "#0d1117", "sidebar_active": "#161b22",
        "border": "#30363d", "input_bg": "#161b22",
    },
    "Ocean": {
        "bg": "#0a1628", "card": "#0f2240", "card_hover": "#142d52",
        "accent": "#00b4d8", "accent_dim": "#0096b7",
        "success": "#48cae4", "error": "#e63946", "warning": "#f4a261",
        "text": "#caf0f8", "text_dim": "#5e8aae",
        "sidebar": "#061020", "sidebar_active": "#0c1a30",
        "border": "#1b3a5c", "input_bg": "#0c1a30",
    },
    "Forest": {
        "bg": "#0d1a0d", "card": "#1a2e1a", "card_hover": "#1f3a1f",
        "accent": "#4caf50", "accent_dim": "#388e3c",
        "success": "#81c784", "error": "#e57373", "warning": "#ffb74d",
        "text": "#c8e6c9", "text_dim": "#6d8b6d",
        "sidebar": "#0a140a", "sidebar_active": "#142814",
        "border": "#2e5a2e", "input_bg": "#142814",
    },
    "Sunset": {
        "bg": "#1a0f0f", "card": "#2e1a1a", "card_hover": "#3a1f1f",
        "accent": "#ff6b6b", "accent_dim": "#e05555",
        "success": "#51cf66", "error": "#ff4757", "warning": "#ffa502",
        "text": "#f5e6cc", "text_dim": "#a08060",
        "sidebar": "#140a0a", "sidebar_active": "#221414",
        "border": "#5a2e2e", "input_bg": "#221414",
    },
    "Purple Haze": {
        "bg": "#12081e", "card": "#1e1030", "card_hover": "#281840",
        "accent": "#bb86fc", "accent_dim": "#9a60d6",
        "success": "#03dac6", "error": "#cf6679", "warning": "#ffab40",
        "text": "#e8dff5", "text_dim": "#7a6a9a",
        "sidebar": "#0a0414", "sidebar_active": "#160c24",
        "border": "#3a2060", "input_bg": "#160c24",
    },
    "Custom": {},
}

COLOR_LABELS = {
    "bg": "Background", "card": "Card", "card_hover": "Card Hover",
    "accent": "Accent", "accent_dim": "Accent Dim",
    "success": "Success", "error": "Error", "warning": "Warning",
    "text": "Text", "text_dim": "Text Dim",
    "sidebar": "Sidebar", "sidebar_active": "Sidebar Active",
    "border": "Border", "input_bg": "Input Background",
}


def load_theme(config):
    name = config.get("theme", "Midnight")
    if name == "Custom":
        custom = config.get("theme_custom", {})
        colors = dict(THEME_PRESETS["Midnight"])
        colors.update(custom)
        return colors
    return dict(THEME_PRESETS.get(name, THEME_PRESETS["Midnight"]))


COLORS = load_theme({})


class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text="", command=None, icon="", **kwargs):
        super().__init__(
            master,
            text=f"  {icon}  {text}" if icon else text,
            command=command,
            fg_color="transparent",
            text_color=COLORS["text_dim"],
            hover_color=COLORS["sidebar_active"],
            anchor="w",
            height=44,
            corner_radius=8,
            font=ctk.CTkFont(size=13),
            **kwargs,
        )
        self.active = False

    def set_active(self, active):
        self.active = active
        if active:
            self.configure(fg_color=COLORS["sidebar_active"], text_color=COLORS["accent"])
        else:
            self.configure(fg_color="transparent", text_color=COLORS["text_dim"])


class LogPanel(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=COLORS["card"], corner_radius=10, **kwargs)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 0))

        ctk.CTkLabel(
            header, text="Output Log",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(side="left")

        ctk.CTkButton(
            header, text="Clear", width=60, height=26,
            fg_color=COLORS["border"], hover_color=COLORS["error"],
            font=ctk.CTkFont(size=11),
            command=self.clear,
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
            state="disabled",
        )
        self.textbox.pack(fill="both", expand=True, padx=10, pady=(6, 10))

    def log(self, message):
        self.textbox.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.textbox.insert("end", f"[{timestamp}] {message}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")


class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Dashboard",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            scroll, text="CPZC Auto Claimer - TikTok Username Scanner & Claimer",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(0, 20))

        stats_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure((0, 1, 2), weight=1)

        self.scanned_label = self._stat_card(stats_frame, "Scanned", "0", 0)
        self.claimed_label = self._stat_card(stats_frame, "Claimed", "0", 1)
        self.errors_label = self._stat_card(stats_frame, "Errors", "0", 2)

        ctk.CTkLabel(
            scroll, text="Quick Actions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(10, 10))

        actions = ctk.CTkFrame(scroll, fg_color="transparent")
        actions.pack(fill="x")
        actions.columnconfigure((0, 1), weight=1)

        self._action_button(actions, "Start Auto Scan", "scan", 0, 0)
        self._action_button(actions, "Generate Usernames", "generate", 0, 1)

        ctk.CTkLabel(
            scroll, text="How to use",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(20, 10))

        steps = [
            "1.  Place your usernames in  data/usernames.txt  (one per line)",
            "2.  Go to  Auto Scan  and log in to TikTok (manual QR, cookies, or credentials)",
            "3.  Configure worker threads and click  Start Scan",
            "4.  The app scans via HTTP and auto-claims available names via the browser",
            "5.  Check  output/claimed.txt  for claimed usernames",
        ]
        for step in steps:
            ctk.CTkLabel(
                scroll, text=step,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_dim"],
                anchor="w",
            ).pack(anchor="w", pady=2)

    def _stat_card(self, parent, label, value, col):
        card = ctk.CTkFrame(parent, fg_color=COLORS["card"], corner_radius=10)
        card.grid(row=0, column=col, padx=6, pady=4, sticky="nsew")

        ctk.CTkLabel(
            card, text=label,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(pady=(14, 0))

        val_label = ctk.CTkLabel(
            card, text=value,
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=COLORS["accent"],
        )
        val_label.pack(pady=(2, 12))
        return val_label

    def _action_button(self, parent, text, page, row, col):
        btn = ctk.CTkButton(
            parent,
            text=text,
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            text_color="#ffffff",
            command=lambda: self.app.navigate_to(page),
        )
        btn.grid(row=row, column=col, padx=6, pady=4, sticky="nsew")

    def update_stats(self, scanned, claimed, errors):
        self.scanned_label.configure(text=str(scanned))
        self.claimed_label.configure(text=str(claimed))
        self.errors_label.configure(text=str(errors))


class AutoScanPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.scanning = False
        self.scan_thread = None
        self._stop_event = threading.Event()

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Auto Scan & Claim",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        login_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        login_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            login_card, text="Login to TikTok",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        self.login_status = ctk.CTkLabel(
            login_card, text="Not logged in",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["error"],
        )
        self.login_status.pack(anchor="w", padx=16, pady=(0, 8))

        btn_frame = ctk.CTkFrame(login_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))
        for i in range(5):
            btn_frame.columnconfigure(i, weight=1)

        login_methods = [
            ("Manual (QR)", "manual"),
            ("Cookies (JSON)", "cookies_json"),
            ("Cookies (sessions)", "cookies_session"),
            ("Create Account", "create"),
            ("Email:Pass File", "credentials"),
        ]
        for i, (text, method) in enumerate(login_methods):
            ctk.CTkButton(
                btn_frame, text=text, height=32,
                corner_radius=6,
                font=ctk.CTkFont(size=11),
                fg_color=COLORS["border"],
                hover_color=COLORS["accent_dim"],
                command=lambda m=method: self._login(m),
            ).grid(row=0, column=i, padx=3, sticky="nsew")

        ctk.CTkButton(
            login_card, text="Save Cookies", height=28, width=100,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_cookies,
        ).pack(anchor="w", padx=16, pady=(0, 12))

        config_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        config_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            config_card, text="Scan Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        cfg_row = ctk.CTkFrame(config_card, fg_color="transparent")
        cfg_row.pack(fill="x", padx=16, pady=(0, 4))

        ctk.CTkLabel(cfg_row, text="Worker Threads:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.threads_var = ctk.StringVar(value="5")
        ctk.CTkEntry(
            cfg_row, textvariable=self.threads_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        usernames_file = os.path.join(SCRIPT_DIR, "data", "usernames.txt")
        file_frame = ctk.CTkFrame(config_card, fg_color="transparent")
        file_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(file_frame, text="Usernames File:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.file_var = ctk.StringVar(value=usernames_file)
        ctk.CTkEntry(
            file_frame, textvariable=self.file_var, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(8, 4), fill="x", expand=True)
        ctk.CTkButton(
            file_frame, text="Browse", width=80, height=30,
            corner_radius=6, font=ctk.CTkFont(size=11),
            fg_color=COLORS["border"], hover_color=COLORS["accent_dim"],
            command=self._browse_file,
        ).pack(side="left")

        self._count_username_file()

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        self.start_btn = ctk.CTkButton(
            action_frame, text="Start Scan", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._start_scan,
        )
        self.start_btn.pack(side="left", padx=(0, 8), expand=True, fill="x")

        self.stop_btn = ctk.CTkButton(
            action_frame, text="Stop", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["error"],
            hover_color="#cc0000",
            command=self._stop_scan,
            state="disabled",
        )
        self.stop_btn.pack(side="left", expand=True, fill="x")

        progress_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        progress_card.pack(fill="x", pady=(0, 12))

        self.progress_label = ctk.CTkLabel(
            progress_card, text="Ready",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_dim"],
        )
        self.progress_label.pack(anchor="w", padx=16, pady=(10, 4))

        self.progress_bar = ctk.CTkProgressBar(
            progress_card, height=8,
            fg_color=COLORS["input_bg"],
            progress_color=COLORS["accent"],
            corner_radius=4,
        )
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))
        self.progress_bar.set(0)

    def _count_username_file(self):
        path = self.file_var.get()
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    count = sum(1 for line in f if line.strip())
                self.progress_label.configure(text=f"Ready — {count} usernames loaded")
            except Exception:
                pass

    def _browse_file(self):
        path = filedialog.askopenfilename(
            initialdir=os.path.join(SCRIPT_DIR, "data"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)
            self._count_username_file()

    def _login(self, method):
        if self.app.claimer and self.app.claimer.driver:
            self.app.claimer.cleanup()
        self.app.claimer = TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )
        self.app.log("Setting up browser...")
        if not self.app.claimer.setup_driver():
            self.app.log("Failed to setup browser")
            messagebox.showerror("Error", "Failed to setup browser. Check Chrome/Chromium is installed.")
            return
        self.app.log("Browser ready")

        def do_login():
            script_dir = SCRIPT_DIR
            logged_in = False
            try:
                if method == "manual":
                    self.app.log("Opening TikTok login page — log in manually in the browser window")
                    self.app.claimer.driver.get("https://www.tiktok.com/login")
                    done = [False]
                    event = threading.Event()
                    def show_manual():
                        messagebox.showinfo(
                            "Manual Login",
                            "Log in to TikTok in the browser window.\nClick OK after you have logged in."
                        )
                        done[0] = True
                        event.set()
                    self.app.after(0, show_manual)
                    event.wait(timeout=300)
                    logged_in = self.app.claimer.verify_logged_in()

                elif method == "cookies_json":
                    path = os.path.join(script_dir, "data", "cookies.json")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_cookies(path)

                elif method == "cookies_session":
                    path = os.path.join(script_dir, "data", "sessions.txt")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_cookies(path)

                elif method == "create":
                    def gui_input(prompt):
                        result = [None]
                        event = threading.Event()
                        def ask():
                            result[0] = simpledialog.askstring("Input Required", prompt)
                            event.set()
                        self.app.after(0, ask)
                        event.wait(timeout=120)
                        return result[0] or ""
                    def gui_pause(prompt):
                        clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                        done = [False]
                        event = threading.Event()
                        def show():
                            messagebox.showinfo("Info", clean)
                            done[0] = True
                            event.set()
                        self.app.after(0, show)
                        event.wait(timeout=30)
                    logged_in = create_account(
                        self.app.claimer.driver, input_fn=gui_input, pause_fn=gui_pause
                    )

                elif method == "credentials":
                    path = os.path.join(script_dir, "data", "accounts.txt")
                    if not os.path.exists(path):
                        self.app.log(f"File not found: {path}")
                        self.app.after(0, lambda: messagebox.showerror("Error", f"File not found:\n{path}"))
                        return
                    logged_in = self.app.claimer.login_with_credentials(path)
            except Exception as e:
                self.app.log(f"Login error: {e}")

            if logged_in:
                self.app.log("Login successful")
                if not self.app.claimer.initialize_edit_profile_setup():
                    self.app.log("Edit profile setup failed")
                    self.app.after(0, lambda: self.login_status.configure(
                        text="Logged in (edit profile failed)", text_color=COLORS["warning"]
                    ))
                else:
                    self.app.after(0, lambda: self.login_status.configure(
                        text=f"Logged in as @{self.app.claimer.current_username}",
                        text_color=COLORS["success"],
                    ))
            else:
                self.app.log("Login failed")
                self.app.after(0, lambda: self.login_status.configure(
                    text="Login failed", text_color=COLORS["error"]
                ))

        threading.Thread(target=do_login, daemon=True).start()

    def _save_cookies(self):
        if not self.app.claimer or not self.app.claimer.driver:
            messagebox.showwarning("Warning", "No browser session to save")
            return
        path = os.path.join(SCRIPT_DIR, "data", "sessions.txt")
        try:
            self.app.claimer.save_cookies(path)
            self.app.log(f"Cookies saved to {path}")
        except Exception as e:
            self.app.log(f"Failed to save cookies: {e}")

    def update_login_status(self, username=None, error=False):
        """Update the login status label from external pages (e.g. Accounts tab)."""
        if error:
            self.app.after(0, lambda: self.login_status.configure(
                text="Login failed", text_color=COLORS["error"]
            ))
        elif username:
            self.app.after(0, lambda: self.login_status.configure(
                text=f"Logged in as @{username}",
                text_color=COLORS["success"],
            ))
        else:
            self.app.after(0, lambda: self.login_status.configure(
                text="Not logged in", text_color=COLORS["text_dim"]
            ))

    def _start_scan(self):
        if self.scanning:
            return
        if not self.app.claimer or not self.app.claimer.driver:
            messagebox.showwarning("Warning", "Please log in first")
            return
        if not self.app.claimer.current_username:
            messagebox.showwarning("Warning", "Edit profile setup required — please re-login")
            return

        usernames_file = self.file_var.get()
        if not os.path.exists(usernames_file):
            messagebox.showwarning("Warning", f"File not found:\n{usernames_file}")
            return

        try:
            threads = int(self.threads_var.get())
            threads = max(1, min(20, threads))
        except ValueError:
            threads = 5

        self.scanning = True
        self._stop_event.clear()
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_label.configure(text="Scanning...", text_color=COLORS["accent"])

        def run():
            self.app.log(f"Starting scan with {threads} workers")
            self.app.claimer.claimed = False
            self.app.claimer.auto_scan_and_claim_mode(usernames_file, self.app.config, threads=threads)
            self.app.after(0, self._scan_finished)

        self.scan_thread = threading.Thread(target=run, daemon=True)
        self.scan_thread.start()

    def _scan_finished(self):
        self.scanning = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if self.app.claimer and self.app.claimer.claimed:
            self.progress_label.configure(text="Username claimed!", text_color=COLORS["success"])
            self.app.log("Username claimed successfully!")
        elif self.app.claimer and self.app.claimer.stop_scan.is_set():
            self.progress_label.configure(text="Scan stopped", text_color=COLORS["warning"])
            self.app.log("Scan stopped by user")
        else:
            self.progress_label.configure(text="Scan finished", text_color=COLORS["text_dim"])
            self.app.log("Scan finished")

    def _stop_scan(self):
        if self.app.claimer:
            self.app.claimer.stop_scan.set()
            self.app.log("Stopping scan...")


class GeneratePage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Generate Usernames",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            card, text="Configuration",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row1, text="Character Set:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.charset_var = ctk.StringVar(value="both")
        ctk.CTkOptionMenu(
            row1, variable=self.charset_var,
            values=["letters", "numbers", "both"],
            width=120, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=4)

        for label, default, attr in [("Min Length:", "4", "min_len"), ("Max Length:", "6", "max_len"), ("Count:", "1000", "count")]:
            ctk.CTkLabel(row2, text=label, font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"]).pack(side="left", padx=(0, 4))
            var = ctk.StringVar(value=default)
            setattr(self, f"_{attr}_var", var)
            ctk.CTkEntry(
                row2, textvariable=var, width=70, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=(0, 12))

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(row3, text="Prefix:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.prefix_var = ctk.StringVar(value="")
        ctk.CTkEntry(
            row3, textvariable=self.prefix_var, width=150, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        action_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        action_frame.pack(fill="x", pady=(0, 12))

        ctk.CTkButton(
            action_frame, text="Generate", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._generate,
        ).pack(side="left", padx=(0, 8), expand=True, fill="x")

        ctk.CTkButton(
            action_frame, text="Save to File", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._save_to_file,
        ).pack(side="left", expand=True, fill="x")

        result_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        result_card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            result_card, text="Generated Usernames",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(10, 4))

        self.result_textbox = ctk.CTkTextbox(
            result_card,
            fg_color=COLORS["input_bg"],
            text_color=COLORS["text"],
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.result_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._generated = []

    def _get_params(self):
        charset = self.charset_var.get()
        if charset == "letters":
            pool = string.ascii_lowercase
        elif charset == "numbers":
            pool = string.digits
        else:
            pool = string.ascii_lowercase + string.digits

        try:
            min_len = max(1, int(self._min_len_var.get()))
        except ValueError:
            min_len = 4
        try:
            max_len = max(min_len, int(self._max_len_var.get()))
        except ValueError:
            max_len = 6
        try:
            count = max(1, int(self._count_var.get()))
        except ValueError:
            count = 1000
        prefix = self.prefix_var.get()

        return pool, min_len, max_len, count, prefix

    def _generate(self):
        pool, min_len, max_len, count, prefix = self._get_params()
        self._generated = []
        for _ in range(count):
            length = random.randint(min_len, max_len)
            u = prefix + "".join(random.choices(pool, k=length))
            self._generated.append(u)

        self.result_textbox.delete("1.0", "end")
        display = self._generated[:200]
        self.result_textbox.insert("1.0", "\n".join(display))
        if count > 200:
            self.result_textbox.insert("end", f"\n\n... and {count - 200} more")
        self.app.log(f"Generated {count} usernames")

    def _save_to_file(self):
        if not self._generated:
            self._generate()
        path = filedialog.asksaveasfilename(
            initialdir=os.path.join(SCRIPT_DIR, "data"),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="usernames.txt",
        )
        if path:
            try:
                with open(path, "w") as f:
                    for u in self._generated:
                        f.write(u + "\n")
                self.app.log(f"Saved {len(self._generated)} usernames to {path}")
                messagebox.showinfo("Saved", f"Saved {len(self._generated)} usernames to:\n{path}")
            except Exception as e:
                self.app.log(f"Save error: {e}")
                messagebox.showerror("Error", str(e))


class AccountsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.accounts = []
        self.selected_idx = None

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Accounts",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        table_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        table_card.pack(fill="both", expand=True, pady=(0, 12))

        header_row = ctk.CTkFrame(table_card, fg_color="transparent")
        header_row.pack(fill="x", padx=16, pady=(12, 4))

        ctk.CTkLabel(header_row, text="Username",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=COLORS["accent"], width=250, anchor="w").pack(side="left")
        ctk.CTkLabel(header_row, text="Email",
                      font=ctk.CTkFont(size=12, weight="bold"),
                      text_color=COLORS["accent"], anchor="w").pack(side="left", padx=(20, 0))

        ctk.CTkFrame(table_card, fg_color=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(0, 4))

        list_frame = ctk.CTkFrame(table_card, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        self.table_canvas = tk.Canvas(list_frame, bg=COLORS["input_bg"], highlightthickness=0)
        self.table_scrollbar = ctk.CTkScrollbar(list_frame, orientation="vertical", command=self.table_canvas.yview)
        self.table_inner = ctk.CTkFrame(self.table_canvas, fg_color="transparent")

        self.table_inner.bind("<Configure>", lambda e: self.table_canvas.configure(scrollregion=self.table_canvas.bbox("all")))
        self.table_canvas_window = self.table_canvas.create_window((0, 0), window=self.table_inner, anchor="nw")
        self.table_canvas.configure(yscrollcommand=self.table_scrollbar.set)

        self.table_canvas.pack(side="left", fill="both", expand=True)
        self.table_scrollbar.pack(side="right", fill="y")

        self.table_canvas.bind("<Configure>", self._on_canvas_resize)

        self.row_widgets = []
        self.empty_label = ctk.CTkLabel(
            self.table_inner, text="No accounts found in data/accounts.txt",
            font=ctk.CTkFont(size=12), text_color=COLORS["text_dim"],
        )

        self.status_label = ctk.CTkLabel(
            table_card, text="",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_dim"],
        )
        self.status_label.pack(anchor="w", padx=16, pady=(0, 8))

        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 12))
        btn_frame.columnconfigure((0, 1), weight=1)

        self.login_btn = ctk.CTkButton(
            btn_frame, text="Login", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._login_account,
        )
        self.login_btn.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        self.inbox_btn = ctk.CTkButton(
            btn_frame, text="Open Inbox", height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["success"],
            hover_color="#00b368",
            text_color="#000000",
            command=self._open_inbox,
        )
        self.inbox_btn.grid(row=0, column=1, padx=(6, 0), sticky="nsew")

        self._load_accounts()

    def _on_canvas_resize(self, event):
        self.table_canvas.itemconfig(self.table_canvas_window, width=event.width)

    def _load_accounts(self):
        self.accounts = []
        path = os.path.join(SCRIPT_DIR, "data", "accounts.txt")
        if not os.path.exists(path):
            self.empty_label.pack(pady=20)
            self.status_label.configure(text="File not found: data/accounts.txt")
            self.inbox_btn.configure(state="disabled")
            return
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if ":" not in line:
                        continue
                    parts = line.split(":", 3)
                    username = parts[0]
                    password = parts[1]
                    email = parts[2] if len(parts) > 2 else ""
                    email_pass = parts[3] if len(parts) > 3 else ""
                    self.accounts.append({
                        "username": username,
                        "password": password,
                        "email": email,
                        "email_pass": email_pass,
                    })
        except Exception as e:
            self.app.log(f"Error loading accounts: {e}")

        if not self.accounts:
            self.empty_label.pack(pady=20)
            self.status_label.configure(text="No valid accounts found")
            self.inbox_btn.configure(state="disabled")
            return

        has_email = any(a["email"] and a["email_pass"] for a in self.accounts)
        if not has_email:
            self.inbox_btn.configure(state="disabled")

        self._build_rows()
        self.status_label.configure(text=f"{len(self.accounts)} accounts loaded")

    def _build_rows(self):
        for w in self.table_inner.winfo_children():
            if w != self.empty_label:
                w.destroy()
        self.row_widgets.clear()
        self.selected_idx = None

        for i, acct in enumerate(self.accounts):
            row_bg = COLORS["input_bg"] if i % 2 == 0 else COLORS["card"]
            row = ctk.CTkFrame(self.table_inner, fg_color=row_bg, corner_radius=0, height=36)
            row.pack(fill="x", pady=0)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=acct["username"],
                          font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"], width=250, anchor="w").pack(side="left", padx=(10, 0))
            ctk.CTkLabel(row, text=acct["email"] or "—",
                          font=ctk.CTkFont(size=12),
                          text_color=COLORS["text_dim"], anchor="w").pack(side="left", padx=(20, 0))

            row.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, idx=i: self._select(idx))

            self.row_widgets.append(row)

    def _select(self, idx):
        if self.selected_idx is not None and self.selected_idx < len(self.row_widgets):
            prev = self.row_widgets[self.selected_idx]
            prev.configure(fg_color=COLORS["input_bg"] if self.selected_idx % 2 == 0 else COLORS["card"])
        self.selected_idx = idx
        self.row_widgets[idx].configure(fg_color=COLORS["accent_dim"])

    def _ensure_driver(self):
        if self.app.claimer and self.app.claimer.driver:
            return True
        self.app.claimer = TikTokSeleniumClaimer(
            headless=self.app.config.get("headless", False),
            username_input_delay=self.app.config.get("username_input_delay", 2),
        )
        self.app.log("Setting up browser...")
        if not self.app.claimer.setup_driver():
            self.app.log("Failed to setup browser")
            return False
        self.app.log("Browser ready")
        return True

    def _login_account(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not self._ensure_driver():
            return

        def do_login():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
            self.app.log(f"Logging in as {acct['username']}...")
            success = self.app.claimer.login_with_single_account(
                acct["username"], acct["password"],
                email=acct.get("email") or None,
                email_password=acct.get("email_pass") or None,
                pause_fn=gui_pause,
                config=self.app.config,
            )
            if success:
                if self.app.claimer.initialize_edit_profile_setup():
                    self.app.after(0, lambda: messagebox.showinfo(
                        "Login Success",
                        f"Logged in as @{self.app.claimer.current_username}"
                    ))
                    self.app.log(f"Logged in as @{self.app.claimer.current_username}")
                    self.app.pages["scan"].update_login_status(self.app.claimer.current_username)
                else:
                    self.app.log("Login succeeded but edit profile setup failed")
                    self.app.pages["scan"].update_login_status(error=True)
            else:
                self.app.log(f"Login failed for {acct['username']}")
                self.app.pages["scan"].update_login_status(error=True)
                self.app.after(0, lambda: messagebox.showerror("Login Failed", f"Could not login as {acct['username']}"))

        threading.Thread(target=do_login, daemon=True).start()

    def _open_inbox(self):
        if self.selected_idx is None:
            messagebox.showwarning("No Selection", "Select an account from the table first")
            return
        acct = self.accounts[self.selected_idx]
        if not acct["email"] or not acct["email_pass"]:
            messagebox.showwarning("No Email", "This account has no email credentials")
            return
        if not self.app.claimer._is_firstmail_email(acct["email"]):
            messagebox.showwarning("Not FirstMail", f"Only FirstMail emails can be used for inbox.\nGot: {acct['email']}")
            return
        if not self._ensure_driver():
            return

        def do_inbox():
            def gui_pause(prompt):
                clean = prompt.replace(Fore.YELLOW, "").replace(Fore.WHITE, "")
                done = [False]
                event = threading.Event()
                def show():
                    messagebox.showinfo("Action Required", clean)
                    done[0] = True
                    event.set()
                self.app.after(0, show)
                event.wait(timeout=300)
            self.app.log(f"Opening inbox for {acct['email']}...")
            self.app.claimer.open_inbox(acct["email"], acct["email_pass"], pause_fn=gui_pause)
            self.app.log("Inbox opened")

        threading.Thread(target=do_inbox, daemon=True).start()


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll, text="Settings",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w", pady=(0, 20))

        theme_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        theme_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            theme_card, text="Theme",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        theme_row = ctk.CTkFrame(theme_card, fg_color="transparent")
        theme_row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(theme_row, text="Preset:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.theme_var = ctk.StringVar(value=self.app.config.get("theme", "Midnight"))
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row, variable=self.theme_var,
            values=list(THEME_PRESETS.keys()),
            width=160, height=30, corner_radius=6,
            fg_color=COLORS["input_bg"],
            button_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
            command=self._on_theme_change,
        )
        self.theme_menu.pack(side="left", padx=(8, 0))

        self.preview_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.preview_frame.pack(fill="x", padx=16, pady=(8, 4))

        self.custom_frame = ctk.CTkFrame(theme_card, fg_color="transparent")
        self.custom_frame.pack(fill="x", padx=16, pady=(0, 4))

        self._color_buttons = {}
        self._build_preview()
        self._build_custom_pickers()
        self._on_theme_change(self.theme_var.get())

        ctk.CTkButton(
            theme_card, text="Apply Theme", height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._apply_theme,
        ).pack(anchor="w", padx=16, pady=(4, 12))

        general_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        general_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            general_card, text="General",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        row = ctk.CTkFrame(general_card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(row, text="Headless Mode:", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.headless_var = ctk.BooleanVar(value=self.app.config.get("headless", False))
        ctk.CTkSwitch(
            row, text="", variable=self.headless_var,
            onvalue=True, offvalue=False,
            button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_dim"],
            fg_color=COLORS["border"],
        ).pack(side="left", padx=(8, 0))

        row2 = ctk.CTkFrame(general_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 12))

        ctk.CTkLabel(row2, text="Username Input Delay (s):", font=ctk.CTkFont(size=12),
                      text_color=COLORS["text"]).pack(side="left")
        self.delay_var = ctk.StringVar(value=str(self.app.config.get("username_input_delay", 2)))
        ctk.CTkEntry(
            row2, textvariable=self.delay_var, width=60, height=30,
            fg_color=COLORS["input_bg"], border_color=COLORS["border"],
            font=ctk.CTkFont(size=12),
        ).pack(side="left", padx=(8, 0))

        notif_card = ctk.CTkFrame(scroll, fg_color=COLORS["card"], corner_radius=10)
        notif_card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            notif_card, text="Notifications",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w", padx=16, pady=(12, 8))

        fields = [
            ("Discord Webhook URL:", "discord_webhook_url"),
            ("Telegram Bot Token:", "telegram_bot_token"),
            ("Telegram Chat ID:", "telegram_chat_id"),
        ]
        self._entries = {}
        for label, key in fields:
            f = ctk.CTkFrame(notif_card, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=4)
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=12),
                          text_color=COLORS["text"], width=180, anchor="w").pack(side="left")
            var = ctk.StringVar(value=self.app.config.get(key, ""))
            self._entries[key] = var
            ctk.CTkEntry(
                f, textvariable=var, height=30,
                fg_color=COLORS["input_bg"], border_color=COLORS["border"],
                font=ctk.CTkFont(size=11),
                show="*" if "token" in key.lower() else "",
            ).pack(side="left", padx=(8, 0), fill="x", expand=True)

        ctk.CTkButton(
            notif_card, text="Save Settings", height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_dim"],
            command=self._save,
        ).pack(anchor="w", padx=16, pady=(8, 12))

    def _build_preview(self):
        for w in self.preview_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.preview_frame, text="Preview",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(0, 4))

        row = ctk.CTkFrame(self.preview_frame, fg_color="transparent")
        row.pack(fill="x")
        for i, (key, label) in enumerate(COLOR_LABELS.items()):
            color = COLORS.get(key, "#888888")
            swatch = ctk.CTkFrame(row, fg_color=color, width=32, height=32, corner_radius=6,
                                   border_width=1, border_color=COLORS["border"])
            swatch.pack(side="left", padx=(0, 2))
            swatch.pack_propagate(False)
        hint = ctk.CTkLabel(
            self.preview_frame, text="Current active colors",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_dim"],
        )
        hint.pack(anchor="w", pady=(4, 0))

    def _build_custom_pickers(self):
        for w in self.custom_frame.winfo_children():
            w.destroy()
        grid = ctk.CTkFrame(self.custom_frame, fg_color="transparent")
        grid.pack(fill="x")
        cols = 4
        for i, (key, label) in enumerate(COLOR_LABELS.items()):
            r, c = divmod(i, cols)
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=r, column=c, padx=4, pady=3, sticky="w")

            color = self.app.config.get("theme_custom", {}).get(key, COLORS.get(key, "#888888"))
            preview = ctk.CTkFrame(cell, fg_color=color, width=20, height=20, corner_radius=4,
                                    border_width=1, border_color=COLORS["border"])
            preview.pack(side="left", padx=(0, 4))
            preview.pack_propagate(False)

            btn = ctk.CTkButton(
                cell, text=label, width=90, height=24,
                corner_radius=4,
                font=ctk.CTkFont(size=10),
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["card_hover"],
                command=lambda k=key, p=preview: self._pick_color(k, p),
            )
            btn.pack(side="left")

    def _pick_color(self, key, preview_widget):
        current = COLORS.get(key, "#888888")
        result = colorchooser.askcolor(initialcolor=current, title=f"Choose {COLOR_LABELS.get(key, key)}")
        if result and result[1]:
            hex_color = result[1]
            COLORS[key] = hex_color
            preview_widget.configure(fg_color=hex_color)
            if not hasattr(self, "_custom_colors"):
                self._custom_colors = {}
            self._custom_colors[key] = hex_color
            self.app.config.setdefault("theme_custom", {})[key] = hex_color

    def _on_theme_change(self, name):
        if name == "Custom":
            self.custom_frame.pack(fill="x", padx=16, pady=(0, 4))
        else:
            self.custom_frame.pack_forget()

    def _apply_theme(self):
        self._save_config()
        self.app.apply_theme()
        self.app.log("Theme applied")

    def _save(self):
        self._save_config()
        self.app.log("Settings saved")
        messagebox.showinfo("Saved", "Settings saved to config.json")

    def _save_config(self):
        self.app.config["headless"] = self.headless_var.get()
        self.app.config["theme"] = self.theme_var.get()
        try:
            self.app.config["username_input_delay"] = float(self.delay_var.get())
        except ValueError:
            pass
        for key, var in self._entries.items():
            self.app.config[key] = var.get()
        if hasattr(self, "_custom_colors"):
            self.app.config.setdefault("theme_custom", {}).update(self._custom_colors)

        config_path = os.path.join(SCRIPT_DIR, "config.json")
        try:
            with open(config_path, "r") as f:
                cfg = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            cfg = {}
        cfg.update(self.app.config)
        with open(config_path, "w") as f:
            json.dump(cfg, f, indent=4)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CPZC Auto Claimer")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.config = load_config()
        self.claimer = None
        global COLORS
        COLORS = load_theme(self.config)
        self.configure(fg_color=COLORS["bg"])

        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))

        ctk.CTkLabel(
            logo_frame, text="CPZC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")

        ctk.CTkLabel(
            logo_frame, text="Auto Claimer",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "home"),
            ("scan", "Auto Scan", "search"),
            ("accounts", "Accounts", "people"),
            ("generate", "Generate", "wand"),
            ("settings", "Settings", "gear"),
        ]
        for page_id, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda p=page_id: self.navigate_to(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn

        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.page_container = ctk.CTkFrame(self.content, fg_color="transparent")
        self.page_container.grid(row=0, column=0, sticky="nsew")
        self.page_container.grid_rowconfigure(0, weight=1)
        self.page_container.grid_columnconfigure(0, weight=1)

        self.log_frame = ctk.CTkFrame(self.content, fg_color="transparent", height=180)
        self.log_frame.grid(row=1, column=0, sticky="sew", padx=10, pady=(0, 10))
        self.log_frame.grid_propagate(False)
        self.log_panel = LogPanel(self.log_frame)
        self.log_panel.pack(fill="both", expand=True)

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.page_container, self)
        self.pages["scan"] = AutoScanPage(self.page_container, self)
        self.pages["accounts"] = AccountsPage(self.page_container, self)
        self.pages["generate"] = GeneratePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.active_page = None
        self.navigate_to("dashboard")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def navigate_to(self, page_id):
        if self.active_page and self.active_page in self.pages:
            self.pages[self.active_page].grid_forget()
        for name, btn in self.nav_buttons.items():
            btn.set_active(name == page_id)
        self.pages[page_id].grid(row=0, column=0, sticky="nsew")
        self.active_page = page_id
        if page_id == "scan" and self.claimer:
            self.pages["scan"]._count_username_file()

    def log(self, message):
        self.log_panel.log(message)

    def _on_close(self):
        if self.claimer and self.claimer.stop_scan:
            self.claimer.stop_scan.set()
        if self.claimer and self.claimer.driver:
            try:
                self.claimer.driver.quit()
            except Exception:
                pass
        self.destroy()

    def apply_theme(self):
        global COLORS
        COLORS = load_theme(self.config)
        self.configure(fg_color=COLORS["bg"])

        self.sidebar.configure(fg_color=COLORS["sidebar"])

        for widget in self.sidebar.winfo_children():
            widget.destroy()

        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=16, pady=(20, 24))
        ctk.CTkLabel(
            logo_frame, text="CPZC",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["accent"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            logo_frame, text="Auto Claimer",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Dashboard", "home"),
            ("scan", "Auto Scan", "search"),
            ("accounts", "Accounts", "people"),
            ("generate", "Generate", "wand"),
            ("settings", "Settings", "gear"),
        ]
        for page_id, label, icon in nav_items:
            btn = SidebarButton(
                self.sidebar, text=label, icon=icon,
                command=lambda p=page_id: self.navigate_to(p),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page_id] = btn

        self.content.configure(fg_color=COLORS["bg"])

        for name, page in self.pages.items():
            page.grid_forget()
            page.destroy()

        self.pages = {}
        self.pages["dashboard"] = DashboardPage(self.page_container, self)
        self.pages["scan"] = AutoScanPage(self.page_container, self)
        self.pages["accounts"] = AccountsPage(self.page_container, self)
        self.pages["generate"] = GeneratePage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

        self.log_panel.destroy()
        self.log_panel = LogPanel(self.log_frame)
        self.log_panel.pack(fill="both", expand=True)

        self.active_page = None
        self.navigate_to("settings")


if __name__ == "__main__":
    app = App()
    app.mainloop()
