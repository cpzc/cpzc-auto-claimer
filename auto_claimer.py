"""
TikTok Username Auto-Claimer

Scans thousands of usernames via HTTP requests and automatically
claims available ones through Selenium browser automation.

Requirements:
    pip install -r requirements.txt

Structure:
    auto_claimer.py    - Main entry point
    config.json        - Runtime settings (delays, etc.)
    data/              - Data files (usernames, accounts, sessions)
    bin/               - Browser drivers (chromedriver.exe)
    output/            - Logs and claimed username records
"""

import time
import re
import json
import threading
import os
import random
import string
import threading
import sys
import requests
import ctypes
from colorama import Fore, init
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, WebDriverException


def load_config():
    """Load runtime settings from config.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

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
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(Fore.YELLOW + f"⚠️ Config error ({e}), using defaults")
        return defaults

    for k, v in defaults.items():
        config.setdefault(k, v)
    return config


TITLE_ART = r"""
 ▄████▄   ██▓███  ▒███████▒ ▄████▄  
▒██▀ ▀█  ▓██░  ██▒▒ ▒ ▒ ▄▀░▒██▀ ▀█  
▒▓█    ▄ ▓██░ ██▓▒░ ▒ ▄▀▒░ ▒▓█    ▄ 
▒▓▓▄ ▄██▒▒██▄█▓▒ ▒  ▄▀▒   ░▒▓▓▄ ▄██▒
▒ ▓███▀ ░▒██▒ ░  ░▒███████▒▒ ▓███▀ ░
░ ░▒ ▒  ░▒▓▒░  ░░▒▒ ▓░▒░▒░ ░▒ ▒  ░
  ░  ▒   ░▒ ░    ░░▒ ▒ ░ ▒  ░  ▒   
░        ░░      ░ ░ ░ ░ ░░       
░ ░              ░ ░   ░ ░        
░                ░     ░          
"""

def draw_border(text):
    lines = text.strip().split('\n')
    if not lines or not lines[0]:
        lines = [""]
    width = max(len(line) for line in lines) + 4
    print(Fore.CYAN + "╔" + "═" * width + "╗")
    for line in lines:
        print(Fore.CYAN + "║ " + Fore.WHITE + line.ljust(width - 2) + Fore.CYAN + " ║")
    print(Fore.CYAN + "╚" + "═" * width + "╝")

def update_title(status=""):
    title_str = f"TikTok Username Claimer"
    if status:
        title_str += f" | {status}"
    ctypes.windll.kernel32.SetConsoleTitleW(title_str)


# --- Account Creation Helpers ---

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
    print(Fore.GREEN + f"Account saved to {filepath}")


def check_rate_limited(driver):
    try:
        text = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "maximum number" in text or "try again later" in text
    except Exception:
        return False


def send_claim_notification(username, config):
    """Send success notification via configured channels."""
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
    """Send CAPTCHA assistance notification via configured channels."""
    message = f"🔒 CAPTCHA requires manual solving!\n{context}\nPlease solve it in the browser."

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


def create_account(claim_driver=None, input_fn=None, pause_fn=None):
    """Create a fresh TikTok account. If claim_driver is given, reuses that browser (no need to re-login).
    input_fn(prompt) -> str: override for input() calls (e.g. GUI dialog). Defaults to built-in input().
    pause_fn(prompt): override for pause/press-Enter prompts. Defaults to input().
    """
    if input_fn is None:
        input_fn = input
    if pause_fn is None:
        pause_fn = input

    print(Fore.CYAN + TITLE_ART)
    draw_border("   CREATE ACCOUNT   \n--------------------\nUsing temp email...")

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

    # Anti-detection (safe to apply even if already applied)
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

        print(Fore.CYAN + "Setting Language to English")
        try:
            lang_select = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[class*='SelectFormContainer']")))
            Select(lang_select).select_by_value("en")
            print(Fore.GREEN + "Language set to English (US)")
        except Exception:
            print(Fore.YELLOW + "Could not set language")
        time.sleep(0.3)

        print(Fore.CYAN + "Setting Birthday")
        select_combobox_value(driver, "Month", "January")
        select_combobox_value(driver, "Day", "1")
        select_combobox_value(driver, "Year", "2000")
        time.sleep(0.3)

        print(Fore.CYAN + "Setting Email Address")
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
            print(Fore.GREEN + f"Using temp email: {email_addr}")
        except Exception as e:
            print(Fore.RED + f"Auto email failed ({e}), using manual input")
            auto_email = False
            email = input_fn(Fore.YELLOW + "Enter your Email: " + Fore.WHITE)
            email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="email"]')))
            email_input.send_keys(email)
            email_addr = email
        time.sleep(0.3)

        print(Fore.CYAN + f"Setting Password: {rngpassword}")
        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(rngpassword)
        time.sleep(0.3)

        try:
            cb = driver.find_element(By.CSS_SELECTOR, 'input#email-consent')
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
                print(Fore.GREEN + "Email consent checked")
                time.sleep(0.2)
        except Exception:
            pass

        try:
            banner = driver.find_element(By.TAG_NAME, "tiktok-cookie-banner")
            driver.execute_script("arguments[0].remove();", banner)
        except Exception:
            pass

        for attempt in range(3):
            print(Fore.CYAN + "Sending verification code...")
            try:
                btn = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-e2e="send-code-button"]')))
                driver.execute_script("arguments[0].click();", btn)
                print(Fore.GREEN + "Sent!")
            except Exception:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                    driver.execute_script("arguments[0].click();", btn)
                    print(Fore.GREEN + "Sent!")
                except Exception as e:
                    print(Fore.RED + f"Could not send: {e}")
            time.sleep(1.5)

            print(Fore.CYAN + "Waiting for verification code (up to 60s)...")
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
                    print(Fore.GREEN + f"Code: {get_code}")
                    break
                else:
                    if attempt < 2:
                        print(Fore.YELLOW + "No code after 60s, refreshing and retrying...")
                        driver.refresh()
                        time.sleep(2)
                        # Re-fill form after refresh
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
                        print(Fore.RED + "Code fetch failed after 3 attempts")
                        if own_driver:
                            driver.quit()
                        else:
                            pause_fn(Fore.YELLOW + "\nPress Enter to return to login...")
                        return False
            else:
                code = input_fn(Fore.YELLOW + "Enter Code from Email: " + Fore.WHITE)
                code_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[placeholder="Enter 6-digit code"]')))
                code_input.send_keys(code)
                break

        time.sleep(2)

        if check_rate_limited(driver):
            print(Fore.RED + "RATE LIMITED")
            return False

        try:
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Next']")))
            next_btn.click()
            time.sleep(3)
        except Exception:
            pass

        if check_rate_limited(driver):
            print(Fore.RED + "RATE LIMITED")
            return False

        username_fields = []
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            try:
                outer = inp.get_attribute("outerHTML").lower()
                if "username" in outer:
                    username_fields.append(inp.get_attribute("name") or inp.get_attribute("id") or "")
            except Exception:
                pass

        birthday_str = "January 1, 2000"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_account(os.path.join(script_dir, "data", "created_accounts.csv"), email_addr, rngpassword, "", email_pass if auto_email else "", birthday_str)
        print(Fore.GREEN + f"\nCredentials: {email_addr} / {rngpassword}")

        if username_fields:
            print(Fore.CYAN + "Signup reached username step.")
        print(Fore.GREEN + "\nAccount created!")

        if own_driver:
            pause_fn(Fore.YELLOW + "\nPress Enter to return...")

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
        self.username_input = None # Store reference to the username input field
        self.edit_profile_modal_open = False # Flag to track if modal is open
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
        """Detect and handle TikTok's 'Verify it's really you' verification flow.

        The verification page shows email/phone option cards. Clicking an email card
        triggers sending a code. Then a code input appears. After entering code,
        overlays may block the submit button — use JS click as fallback.
        """
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
                            if (src.includes('captcha') || src.includes('challenge') || src.includes('slider') || src.includes('verify')) {
                                return true;
                            }
                        }
                        var captchaEls = document.querySelectorAll('[class*="captcha"], [class*="challenge"], [id*="captcha"], [class*="slider"], [class*="secsdk"]');
                        for (var j = 0; j < captchaEls.length; j++) {
                            if (captchaEls[j].offsetParent !== null) return true;
                        }
                        return false;
                    """)
                except Exception:
                    pass

                if has_captcha:
                    print(Fore.YELLOW + "   🔒 CAPTCHA detected — please solve the slider puzzle in the browser")
                    if config:
                        send_captcha_notification(config, f"Account login verification for TikTok")
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
                            if (src.includes('captcha') || src.includes('challenge') || src.includes('slider') || src.includes('verify')) {
                                return true;
                            }
                        }
                        var captchaEls = document.querySelectorAll('[class*="captcha"], [class*="challenge"], [id*="captcha"], [class*="slider"], [class*="secsdk"]');
                        for (var j = 0; j < captchaEls.length; j++) {
                            if (captchaEls[j].offsetParent !== null) return true;
                        }
                        return false;
                    """)
                except Exception:
                    pass

                if post_captcha:
                    print(Fore.YELLOW + "   🔒 CAPTCHA appeared after code submission — please solve the slider puzzle")
                    if config:
                        send_captcha_notification(config, f"Post-code CAPTCHA for TikTok verification")
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
        """Dismiss FirstMail cookie/consent banners."""
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

    def _fill_firstmail_credentials(self, email, email_password):
        """Fill FirstMail login form and submit."""
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
        """Search the current page body for a 6-digit verification code. Returns code or None."""
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            codes_found = re.findall(r'\b\d{6}\b', body_text)
            if codes_found:
                return codes_found[0]
        except Exception:
            pass
        return None

    def _get_code_from_inbox(self, email, email_password, pause_fn=None):
        """Open FirstMail in a new tab, login, find the latest TikTok verification code."""
        if pause_fn is None:
            pause_fn = input
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
        """Open FirstMail webmail in the current tab, pause for CAPTCHA, then login."""
        if pause_fn is None:
            pause_fn = input
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
        """Save current cookies to a JSON file"""
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
        """Wait for user to login manually"""
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
        """Check if user is logged in without navigating away from current page"""
        try:
            time.sleep(1)
            current_url = self.driver.current_url.lower()
            if "login" not in current_url:
                return True

            # Only navigate to /setting as a fallback
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
        """Get current username from settings page"""
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
        """Check if username is available"""
        print(f"\n🔍 Checking if @{username} is available...")
        
        try:
            # Visit the profile page
            self.driver.get(f"https://www.tiktok.com/@{username}")
            time.sleep(1)
            
            page_source = self.driver.page_source.lower()
            
            # Check for "couldn't find this account" or similar
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
            
            # If we can see user content, it's taken
            if "video" in page_source or "followers" in page_source:
                print(f"   ❌ Username is taken")
                return False, "Username is already taken"
            
            print(f"   ⚠️ Status unclear - attempting claim anyway")
            return True, "Status uncertain"
            
        except Exception as e:
            print(f"   ⚠️ Error checking: {e}")
            return True, "Check failed - attempting claim"
    
    def has_ready_username_input(self):
        """Return True when the stored username field is still usable."""
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
        """Find and store the username input in the already-open Edit Profile screen."""
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
        """One-time startup setup: verify account, open Edit Profile, and cache the username field."""
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
        """Navigate to the edit profile modal"""
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
        """Attempt to claim a username"""
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
        """Threaded check using requests (matching checker.py method)."""
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
        """Auto scan mode - uses requests + threading (like checker.py), claims via Selenium."""

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
        """Close the browser"""
        if self.driver:
            print("\n🧹 Cleaning up...")
            try:
                self.driver.quit()
                print("   ✅ Browser closed")
            except Exception:
                pass
