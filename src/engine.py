"""Core TikTok Selenium claimer engine — driver setup, login, claiming, scanning."""

import ctypes
import json
import os
import re
import threading
import time
from datetime import datetime

import requests
from colorama import Fore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException

from src.config import SCRIPT_DIR, get_app_instance
from src.notifications import send_captcha_notification, send_claim_notification
from src.utils import draw_border


class TikTokSeleniumClaimer:
    def __init__(self, headless=False, username_input_delay=2):
        self.headless = headless
        self.username_input_delay = float(username_input_delay)
        self.driver = None
        self.current_username = None
        self.claimed = False
        self.stop_scan = threading.Event()
        self.pause_scan = threading.Event()
        self.username_input = None
        self.scan_scanned = 0
        self.scan_claimed = 0
        self.scan_errors = 0
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

    # ── Browser Setup ─────────────────────────────────────────────────────

    def setup_driver(self):
        print(Fore.CYAN + "\n\U0001f310 Setting up browser...")

        chrome_options = Options()

        chromium_path = r"C:\Program Files\Chromium\Application\chrome.exe"
        if os.path.exists(chromium_path):
            chrome_options.binary_location = chromium_path
            print(Fore.WHITE + "   \u2705 Found Chromium")
        else:
            print(Fore.WHITE + "   \u2139\ufe0f Using default Chrome (Chromium not found)")

        if self.headless:
            chrome_options.add_argument("--headless=new")
            print(Fore.WHITE + "   \U0001f576\ufe0f Headless mode")
        else:
            print(Fore.WHITE + "   \U0001f441\ufe0f Visible mode")

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option(
            "excludeSwitches", ["enable-automation"]
        )
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        chrome_options.add_argument("--start-minimized")
        chrome_options.add_experimental_option("detach", True)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(15)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            print(Fore.GREEN + "   \u2705 Browser ready!")
            return True
        except Exception as e:
            print(Fore.RED + f"   \u274c Error: {e}")
            return False

    # ── Login Methods ─────────────────────────────────────────────────────

    def login_with_cookies(self, cookies_file):
        print(Fore.CYAN + "\n\U0001f511 Loading session from cookies...")
        try:
            self.driver.get("https://www.tiktok.com")
            time.sleep(1)

            with open(cookies_file, "r") as f:
                cookies = json.load(f)

            print(Fore.WHITE + f"   \U0001f4e6 {len(cookies)} cookies")

            for cookie in cookies:
                try:
                    cookie_dict = {
                        "name": cookie["name"],
                        "value": cookie["value"],
                        "domain": cookie.get("domain", ".tiktok.com"),
                        "path": cookie.get("path", "/"),
                        "secure": cookie.get("secure", False),
                    }
                    if "expirationDate" in cookie and cookie["expirationDate"]:
                        cookie_dict["expiry"] = int(cookie["expirationDate"])
                    self.driver.add_cookie(cookie_dict)
                except Exception:
                    continue

            self.driver.refresh()
            time.sleep(1.5)

            print(Fore.GREEN + "   \u2705 Cookies loaded!")
            return True

        except Exception as e:
            print(Fore.RED + f"   \u274c Error loading cookies: {e}")
            return False

    def login_with_single_account(
        self,
        username,
        password,
        email=None,
        email_password=None,
        pause_fn=None,
        input_fn=None,
        config=None,
    ):
        if pause_fn is None:
            pause_fn = input
        if input_fn is None:
            input_fn = input
        print(Fore.CYAN + f"\nLogging in as {username}...")
        try:
            self.driver.get("https://www.tiktok.com/login/phone-or-email/email")
            time.sleep(3)

            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[name="username"]')
                )
            )
            email_input.send_keys(username)
            time.sleep(0.3)
            self.driver.find_element(
                By.CSS_SELECTOR, 'input[type="password"]'
            ).send_keys(password)

            login_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button[data-e2e="login-button"]')
                )
            )
            login_btn.click()
            time.sleep(5)

            page_url = self.driver.current_url.lower()
            body_text = ""
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            except Exception:
                pass

            is_verification = (
                "verify" in body_text
                or "really you" in body_text
                or "security" in body_text
                or "verification" in body_text
                or "send code" in body_text
                or "confirm" in body_text
            )
            is_login_page = "login" in page_url

            if is_verification and is_login_page:
                print(Fore.CYAN + "   \U0001f510 Verification screen detected on login page")
                verification_handled = self._handle_login_verification(
                    email, email_password, pause_fn, input_fn=input_fn, config=config
                )
                if verification_handled:
                    logged_in_user = self.get_current_username()
                    if logged_in_user and logged_in_user.lower() != username.lower():
                        print(
                            Fore.RED
                            + f"   \u274c Logged into wrong account: @{logged_in_user} (expected @{username})"
                        )
                        return False
                    if self.verify_logged_in():
                        print(
                            Fore.GREEN
                            + f"   \u2705 Login successful (via verification): {username}"
                        )
                        return True
                print(Fore.YELLOW + f"   \u274c Verification did not complete login")
                return False

            if not is_login_page:
                logged_in_user = self.get_current_username()
                if logged_in_user and logged_in_user.lower() != username.lower():
                    print(
                        Fore.RED
                        + f"   \u274c Logged into wrong account: @{logged_in_user} (expected @{username})"
                    )
                    return False
                if self.verify_logged_in():
                    print(Fore.GREEN + f"   \u2705 Login successful: {username}")
                    return True

            print(Fore.YELLOW + f"   \u274c Failed: {username}")
            return False
        except Exception as e:
            print(Fore.YELLOW + f"   \u274c Error: {e}")
            return False

    # ── Verification Handling ─────────────────────────────────────────────

    def _handle_login_verification(
        self,
        email=None,
        email_password=None,
        pause_fn=None,
        input_fn=None,
        config=None,
    ):
        if pause_fn is None:
            pause_fn = input
        if input_fn is None:
            input_fn = input
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if (
                "verify" not in body_text.lower()
                and "really you" not in body_text.lower()
            ):
                return False

            print(
                Fore.CYAN
                + "   \U0001f510 Verification required - 'Verify it's really you' detected"
            )

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
                            if "@" in div_text and div.is_displayed():
                                classes = div.get_attribute("class") or ""
                                if "item" in classes.lower() or "home" in classes.lower():
                                    email_option = div
                                    break
                        except Exception:
                            continue
                except Exception:
                    pass

            if email_option:
                print(
                    Fore.CYAN
                    + f"   \U0001f4e9 Clicking email option: {email_option.text[:50]}..."
                )
                try:
                    email_option.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", email_option)
                time.sleep(5)

                has_captcha = self._detect_captcha()

                if has_captcha:
                    print(
                        Fore.YELLOW
                        + "   CAPTCHA detected - please solve the slider puzzle in the browser"
                    )
                    if config:
                        send_captcha_notification(
                            config, "Account login verification for TikTok"
                        )
                    pause_fn(
                        Fore.YELLOW
                        + "   Solve the CAPTCHA puzzle in the browser, then press Enter here to continue..."
                    )
                    time.sleep(2)
                else:
                    print(Fore.CYAN + "   No CAPTCHA, waiting for email to arrive...")
                    time.sleep(3)
            else:
                print(
                    Fore.YELLOW
                    + "   No email option card found, code may already be sent or page layout differs"
                )

            max_retries = 3
            for attempt in range(max_retries):
                code = None
                if email and email_password:
                    code = self._get_code_from_inbox(
                        email, email_password, pause_fn
                    )
                else:
                    if attempt == 0:
                        print(
                            Fore.YELLOW
                            + "\n   \u26a0\ufe0f  No email credentials for this account."
                        )
                        pause_fn(
                            Fore.YELLOW
                            + "   A verification code was sent to the account's email. Solve CAPTCHA in browser if needed, then press Enter..."
                        )
                    code = input_fn(
                        Fore.CYAN + "   Enter the 6-digit verification code: "
                    ).strip()

                if not code:
                    print(Fore.RED + "   \u274c No verification code obtained")
                    return False

                print(
                    Fore.CYAN
                    + f"   Entering code: {code} (attempt {attempt+1}/{max_retries})"
                )
                time.sleep(2)

                code_input = self._find_code_input()
                if not code_input:
                    print(
                        Fore.RED + "   \u274c Could not find verification code input field"
                    )
                    return False

                self._enter_code(code_input, code)
                time.sleep(1)

                print(Fore.CYAN + "   Submitting verification code...")
                time.sleep(2)

                next_btn = self._wait_for_next_button()
                submit_success = self._click_next(next_btn, code_input)

                if not submit_success:
                    try:
                        code_input.submit()
                    except Exception:
                        pass

                time.sleep(3)

                post_captcha = self._detect_captcha()
                if post_captcha:
                    print(
                        Fore.YELLOW
                        + "   CAPTCHA appeared after code submission - please solve the slider puzzle"
                    )
                    if config:
                        send_captcha_notification(
                            config, "Post-code CAPTCHA for TikTok verification"
                        )
                    pause_fn(
                        Fore.YELLOW
                        + "   Solve the CAPTCHA in the browser, then press Enter here to continue..."
                    )
                    time.sleep(3)

                time.sleep(2)

                page_text = ""
                try:
                    page_text = self.driver.find_element(
                        By.TAG_NAME, "body"
                    ).text.lower()
                except Exception:
                    pass

                if "expired" in page_text or "incorrect" in page_text:
                    print(
                        Fore.YELLOW
                        + f"   \u26a0\ufe0f  Code expired or incorrect \u2014 fetching new code from inbox..."
                    )
                    time.sleep(3)
                    continue

                if self.verify_logged_in():
                    return True

                still_on_verification = (
                    "verify" in page_text or "really you" in page_text
                )
                if still_on_verification:
                    print(
                        Fore.YELLOW
                        + f"   \u26a0\ufe0f  Still on verification page \u2014 retrying with new code..."
                    )
                    time.sleep(3)
                    continue

                print(Fore.YELLOW + "   Page changed, checking login status...")
                if self.verify_logged_in():
                    return True

                print(
                    Fore.RED
                    + "   \u274c Unexpected page state after code submission"
                )
                return False

            print(Fore.RED + f"   \u274c All {max_retries} attempts failed")
            return False

        except Exception as e:
            print(Fore.YELLOW + f"   \u26a0\ufe0f  Verification handling error: {e}")
            return False

    def _detect_captcha(self):
        try:
            return self.driver.execute_script("""
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
        except Exception:
            return False

    def _find_code_input(self):
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
                        return c
            except Exception:
                continue

        try:
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            for inp in inputs:
                try:
                    ml = inp.get_attribute("maxlength")
                    if ml and int(ml) <= 8 and inp.is_displayed():
                        return inp
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _enter_code(self, code_input, code):
        try:
            code_input.click()
            time.sleep(0.5)
            self.driver.execute_script(
                """
                var input = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(input, arguments[1]);
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
                input.dispatchEvent(new KeyboardEvent('keydown', {bubbles: true}));
                input.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
                input.dispatchEvent(new Event('blur', {bubbles: true}));
                input.dispatchEvent(new Event('focus', {bubbles: true}));
            """,
                code_input,
                code,
            )
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

    def _wait_for_next_button(self):
        next_btn = None
        for wait in range(10):
            try:
                all_btns = self.driver.find_elements(By.CSS_SELECTOR, "button")
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
                        print(
                            Fore.GREEN
                            + f"   \u2705 Next button enabled (attempt {wait+1})"
                        )
                        break
                    else:
                        print(
                            Fore.YELLOW
                            + f"   Next button still disabled, waiting... ({wait+1}/10)"
                        )
            except Exception:
                pass
            time.sleep(1)
        return next_btn

    def _click_next(self, next_btn, code_input):
        submit_success = False
        if next_btn:
            try:
                is_disabled = next_btn.get_attribute("disabled")
                if is_disabled is not None:
                    print(Fore.YELLOW + "   Button still disabled, forcing click via JS...")
                    self.driver.execute_script(
                        "arguments[0].disabled = false; arguments[0].click();", next_btn
                    )
                    submit_success = True
                else:
                    next_btn.click()
                    submit_success = True
            except Exception:
                self.driver.execute_script(
                    "arguments[0].disabled = false; arguments[0].click();", next_btn
                )
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
        return submit_success

    # ── FirstMail Inbox ───────────────────────────────────────────────────

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
            code_match = re.search(
                r"(?:code|verification|verify)\D*(\d{6})", body_text, re.IGNORECASE
            )
            if code_match:
                return code_match.group(1)
            codes_found = re.findall(r"\b\d{6}\b", body_text)
            if codes_found:
                return codes_found[0]
        except Exception:
            pass
        return None

    def _get_code_from_inbox(self, email, email_password, pause_fn=None):
        if pause_fn is None:
            pause_fn = input
        if not self._is_firstmail_email(email):
            print(
                Fore.RED
                + f"   Only FirstMail emails can be used for inbox (got: {email})"
            )
            return None
        print(Fore.CYAN + "   \U0001f4e7 Opening FirstMail inbox in new tab...")
        original_window = self.driver.current_window_handle

        try:
            self.driver.execute_script(
                "window.open('https://firstmail.ltd/ru-RU/webmail/login', '_blank');"
            )
            time.sleep(1)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            time.sleep(3)

            self._dismiss_cookie_banner()
            pause_fn(
                Fore.YELLOW
                + "\n   Solve the CAPTCHA on the FirstMail tab if needed, then press Enter here to continue..."
            )
            self._fill_firstmail_credentials(email, email_password)

            print(Fore.CYAN + "   Looking for TikTok verification email...")
            code = None
            for attempt in range(5):
                try:
                    code = self._search_for_code()
                    if code:
                        print(Fore.GREEN + f"   \u2705 Found verification code: {code}")
                        return code

                    email_rows = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        'tr, [class*="message"], [class*="mail-item"], [class*="email"]',
                    )
                    for row in email_rows:
                        try:
                            row_text = row.text.lower()
                            if (
                                "tiktok" in row_text
                                or "verification" in row_text
                                or "verify" in row_text
                            ):
                                print(
                                    Fore.CYAN
                                    + f"   Found TikTok email: {row.text[:60]}..."
                                )
                                row.click()
                                time.sleep(3)
                                email_body = self.driver.find_element(
                                    By.TAG_NAME, "body"
                                ).text
                                codes_found = re.findall(r"\b\d{6}\b", email_body)
                                if codes_found:
                                    code = codes_found[0]
                                    print(
                                        Fore.GREEN
                                        + f"   \u2705 Extracted verification code: {code}"
                                    )
                                    return code
                        except Exception:
                            continue

                    print(
                        Fore.YELLOW
                        + f"   Attempt {attempt+1}/5: Waiting for email to arrive..."
                    )
                    time.sleep(5)
                    try:
                        refresh_btn = self.driver.find_element(
                            By.CSS_SELECTOR,
                            'button[class*="refresh"], a[class*="refresh"], [data-action="refresh"]',
                        )
                        refresh_btn.click()
                    except Exception:
                        self.driver.refresh()
                    time.sleep(3)

                except Exception as e:
                    print(
                        Fore.YELLOW
                        + f"   Attempt {attempt+1}/5: Error searching emails: {e}"
                    )
                    time.sleep(5)

            return None

        except Exception as e:
            print(Fore.RED + f"   \u274c Error accessing inbox: {e}")
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
            print(
                Fore.RED
                + f"   Only FirstMail emails can be used for inbox (got: {email})"
            )
            return False
        print(Fore.CYAN + "\nOpening FirstMail webmail...")
        try:
            self.driver.get("https://firstmail.ltd/ru-RU/webmail/login")
            time.sleep(3)

            self._dismiss_cookie_banner()
            pause_fn(
                Fore.YELLOW
                + "\nSolve the CAPTCHA in the browser, then press Enter to continue..."
            )
            self._fill_firstmail_credentials(email, email_password)

            print(Fore.GREEN + "   \u2705 Inbox login submitted")
            return True
        except Exception as e:
            print(Fore.RED + f"   \u274c Inbox login error: {e}")
            return False

    # ── Cookies ───────────────────────────────────────────────────────────

    def save_cookies(self, filepath):
        try:
            cookies = self.driver.get_cookies()
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                json.dump(cookies, f, indent=2)
            print(Fore.GREEN + f"   \u2705 Cookies saved ({len(cookies)})")
            return True
        except Exception as e:
            print(Fore.RED + f"   \u274c Failed to save cookies: {e}")
            return False

    # ── Manual Login ──────────────────────────────────────────────────────

    def manual_login(self, pause_fn=None):
        if pause_fn is None:
            pause_fn = input
        print(Fore.CYAN + "\n\U0001f510 Manual Login Required")
        print(Fore.CYAN + "=" * 60)
        print(Fore.WHITE + "Please login to TikTok in the browser window that opened.")
        print("  \u2022 QR Code")
        print("  \u2022 Phone/Email/Username")
        print("  \u2022 Social media accounts")
        print(Fore.YELLOW + "\nOnce logged in, press Enter here to continue...")
        print(Fore.CYAN + "=" * 60)

        try:
            self.driver.get("https://www.tiktok.com/login")
            pause_fn(Fore.WHITE + "\n\u23f8\ufe0f  Press Enter after you've logged in: ")
            time.sleep(1)
            return self.verify_logged_in()

        except Exception as e:
            print(Fore.RED + f"\u274c Error during manual login: {e}")
            return False

    # ── Auth State Checks ─────────────────────────────────────────────────

    def verify_logged_in(self):
        try:
            time.sleep(1)
            current_url = self.driver.current_url.lower()
            if "login" not in current_url:
                return True

            try:
                self.driver.set_page_load_timeout(10)
                self.driver.get("https://www.tiktok.com/settings")
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
        print(Fore.CYAN + "\n\U0001f4cb Fetching current username...")

        try:
            self.driver.get("https://www.tiktok.com/setting")
            time.sleep(1.5)

            page_source = self.driver.page_source

            patterns = [
                r'"uniqueId"\s*:\s*"([a-zA-Z0-9_\.]{2,})"',
                r"@([a-zA-Z0-9_\.]{2,})",
            ]

            for pattern in patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    valid = [
                        m
                        for m in matches
                        if m.lower() not in ["tiktok", "user", "profile", "settings"]
                    ]
                    if valid:
                        username = max(valid, key=len).lower()
                        print(Fore.GREEN + f"   \u2705 @{username}")
                        return username

            try:
                username_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[type='text'][placeholder*='sername']"
                )
                username = username_input.get_attribute("value")
                if username:
                    print(Fore.GREEN + f"   \u2705 @{username}")
                    return username.lower()
            except Exception:
                pass

            print(Fore.YELLOW + "   \u26a0\ufe0f Could not detect username")
            return None

        except Exception as e:
            print(Fore.RED + f"   \u274c Error: {e}")
            return None

    # ── Username Availability ─────────────────────────────────────────────

    def check_username_availability(self, username):
        print(f"\n\U0001f50d Checking if @{username} is available...")

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
                    print(f"   \u2705 Username appears to be available!")
                    return True, "Available"

            if (
                "followbutton" in page_source
                or "follow-count" in page_source
                or '"uniqueId"' in page_source
            ):
                print(f"   \u274c Username is taken")
                return False, "Username is already taken"

            print(f"   \u26a0\ufe0f Status unclear - attempting claim anyway")
            return True, "Status uncertain"

        except Exception as e:
            print(f"   \u26a0\ufe0f Error checking: {e}")
            return True, "Check failed - attempting claim"

    # ── Edit Profile / Username Input ─────────────────────────────────────

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
                if selector.startswith("//"):
                    username_input = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                else:
                    username_input = WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )

                if (
                    username_input
                    and username_input.is_displayed()
                    and username_input.is_enabled()
                ):
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
        print(Fore.CYAN + "\n" + "=" * 60)
        print(Fore.WHITE + "Initial setup: opening Edit Profile once")
        print(Fore.CYAN + "=" * 60)

        if not self.verify_logged_in():
            return False

        detected_username = self.get_current_username()
        if not detected_username:
            print(Fore.YELLOW + "   \u26a0\ufe0f Could not detect username")
            return False

        if self.current_username and detected_username != self.current_username:
            print(
                Fore.RED
                + f"   \u274c Account mismatch: @{detected_username} (expected @{self.current_username})"
            )
            return False

        self.current_username = detected_username
        print(Fore.GREEN + f"   \u2705 @{self.current_username}")

        if not self.navigate_to_edit_profile():
            return False

        return self.has_ready_username_input()

    def navigate_to_edit_profile(self):
        if self.has_ready_username_input():
            return True

        print(Fore.CYAN + "\n\U0001f4cd Initializing profile navigation...")
        self.edit_profile_modal_open = False

        try:
            if not self.current_username:
                print(Fore.WHITE + "   \U0001f50d Getting current username...")
                self.current_username = self.get_current_username()
                if not self.current_username:
                    print(
                        Fore.YELLOW
                        + "   \u26a0\ufe0f Could not get username, going to main page"
                    )
                    self.driver.get("https://www.tiktok.com")
                    time.sleep(1.5)

            if self.current_username:
                profile_url = f"https://www.tiktok.com/@{self.current_username}"
                print(Fore.WHITE + f"   \U0001f517 {profile_url}")
                self.driver.get(profile_url)
                time.sleep(1.5)
            else:
                self.driver.get("https://www.tiktok.com")
                time.sleep(1.5)

            print(Fore.WHITE + "   \U0001f50d Looking for Edit profile...")

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
                    if selector.startswith("//"):
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        edit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, selector)
                            )
                        )
                    if edit_button:
                        break
                except Exception:
                    continue

            if not edit_button:
                print(Fore.YELLOW + "   \u26a0\ufe0f Could not find Edit profile button")
                return False

            print(Fore.WHITE + "   \U0001f5b1\ufe0f Clicking Edit profile...")
            edit_button.click()
            time.sleep(1)

            if not self.find_username_input(timeout=5):
                print(
                    Fore.YELLOW
                    + "   \u26a0\ufe0f Username input not found after opening modal"
                )
                return False

            print(Fore.GREEN + "   \u2705 Edit profile modal opened!")
            return True

        except Exception as e:
            print(Fore.RED + f"   \u274c Error navigating: {e}")
            return False

    # ── Claim Username ────────────────────────────────────────────────────

    def claim_username(self, username, skip_availability_check=False, quiet=False):
        username = username.replace("@", "").strip().lower()

        if not quiet:
            print(Fore.CYAN + f"\n{'='*60}")
            print(Fore.WHITE + f"\U0001f3af Claiming: @{username}")
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

            self.driver.execute_script(
                """
                var inp = arguments[0];
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(inp, arguments[1]);
                inp.dispatchEvent(new Event('input', { bubbles: true }));
                inp.dispatchEvent(new Event('change', { bubbles: true }));
                inp.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true }));
                inp.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true }));
                inp.dispatchEvent(new Event('blur', { bubbles: true }));
                inp.dispatchEvent(new Event('focus', { bubbles: true }));
            """,
                inp,
                username,
            )
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
                print(
                    Fore.WHITE
                    + f"\u23f3 Waiting {self.username_input_delay}s for validation..."
                )
            time.sleep(self.username_input_delay)

            if not quiet:
                print(Fore.WHITE + "\U0001f50d Looking for Save button...")
            save = None
            for sel in [
                "//button[contains(text(), 'Save')]",
                "button[type='submit']",
                "//button[contains(@class, 'save')]",
            ]:
                try:
                    if sel.startswith("//"):
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
                print(Fore.WHITE + "\U0001f5b1\ufe0f Clicking Save...")
            save.click()
            time.sleep(1.5)

            if "30 days" in self.driver.page_source.lower():
                for sel in [
                    "//button[contains(text(), 'Confirm')]",
                    "button[data-e2e='confirm']",
                ]:
                    try:
                        btn = (
                            self.driver.find_element(By.XPATH, sel)
                            if sel.startswith("//")
                            else self.driver.find_element(By.CSS_SELECTOR, sel)
                        )
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
                modal = self.driver.find_element(
                    By.CSS_SELECTOR, "div[role='dialog']"
                )
                if "auto-moderat" in modal.text.lower():
                    self.driver.find_element(
                        By.CSS_SELECTOR, "button[aria-label='Close']"
                    ).click()
                    return False, "Auto-moderated by TikTok"
            except Exception:
                pass

            return False, "Claim failed"

        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    # ── Threaded Check ────────────────────────────────────────────────────

    def check_username_threaded(self, username, session):
        endpoint = "https://www.tiktok.com/@"
        try:
            request = session.get(endpoint + username, timeout=(3, 5))
            if request.status_code == 404:
                return username, True
            if request.status_code == 200:
                text = request.text.lower()
                if any(
                    kw in text
                    for kw in ["followingcount", "followercount", "video__ns"]
                ):
                    return username, False
                else:
                    return username, True
            else:
                return username, None
        except Exception:
            return username, None

    # ── Auto Scan & Claim ─────────────────────────────────────────────────

    def auto_scan_and_claim_mode(self, usernames_file, config=None, threads=None):
        print("\n" + "=" * 60)
        print("\U0001f50d Auto Scan & Claim Mode")
        print("=" * 60)
        print(f"\U0001f4c1 Reading usernames from: {usernames_file}")
        print("\U0001f4a1 Checking via HTTP requests + threading (checker.py method)")
        print("\U0001f6d1 Press Ctrl+C to stop\n")

        usernames = []
        try:
            with open(usernames_file, "r") as f:
                for line in f:
                    u = line.strip().lower().replace("@", "")
                    if u and u.replace("_", "").replace(".", "").isalnum():
                        usernames.append(u)
        except FileNotFoundError:
            print(f"\u274c File not found: {usernames_file}")
            return

        if not usernames:
            print("\u274c No valid usernames found in file")
            return

        print(f"\U0001f4ca Loaded {len(usernames)} usernames\n")

        self.claimed = False
        self.stop_scan.clear()
        self.pause_scan.clear()
        self.scan_scanned = 0
        self.scan_claimed = 0
        self.scan_errors = 0

        if threads is None:
            if get_app_instance():
                threads = 5
            else:
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

        claim_log = os.path.join(SCRIPT_DIR, "output", "claimed.txt")
        error_log = os.path.join(SCRIPT_DIR, "output", "errors.log")
        os.makedirs(os.path.join(SCRIPT_DIR, "output"), exist_ok=True)

        lock = threading.RLock()
        claiming_event = threading.Event()
        claiming_event.set()
        checked = 0
        total = len(usernames)
        error_cooldown = 0.0
        thread_local = threading.local()

        def get_session():
            if not hasattr(thread_local, "session"):
                thread_local.session = requests.Session()
                thread_local.session.headers.update(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                )
            return thread_local.session

        def safe_print(*args, **kwargs):
            with lock:
                print(*args, **kwargs, flush=True)

        def update_title():
            title = (
                f"Checking {checked}/{total} | "
                f"{'CLAIMED' if self.claimed else 'Scanning'}"
            )
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

            while self.pause_scan.is_set() and not self.stop_scan.is_set():
                time.sleep(0.5)

            wait_cooldown()

            time.sleep(0.3)

            result = self.check_username_threaded(username, get_session())

            with lock:
                checked += 1
                current = checked
                self.scan_scanned = checked
            update_title()

            _, available = result

            if available is True:
                with lock:
                    if self.claimed or not claiming_event.is_set():
                        return
                    claiming_event.clear()
                safe_print(
                    f"  \u2705 [{current}/{total}] @{username} \u2014 AVAILABLE, claiming..."
                )
                try:
                    success, msg = self.claim_username(
                        username, skip_availability_check=True, quiet=True
                    )
                except Exception as e:
                    success, msg = False, f"Claim crashed: {e}"
                safe_print(
                    f"     \U0001f389 Claimed @{username}!"
                    if success
                    else f"     \u23ed\ufe0f {msg}"
                )
                if success:
                    safe_print(
                        f"     \U0001f517 https://www.tiktok.com/@{username}"
                    )
                    self.claimed = True
                    self.scan_claimed += 1
                    update_title()
                    try:
                        with open(claim_log, "a") as f:
                            f.write(
                                f"{datetime.now().isoformat()} @{username}\n"
                            )
                    except Exception:
                        pass
                    if config:
                        send_claim_notification(username, config)
                claiming_event.set()
            elif available is False:
                safe_print(f"  \u274c [{current}/{total}] @{username}")
            else:
                with lock:
                    self.scan_errors += 1
                    wait_secs = min(15, max(3, checked // 20 * 2))
                    error_cooldown = time.time() + wait_secs
                    safe_print(
                        f"  \u26a0\ufe0f [{current}/{total}] @{username} \u2014 error (waiting {wait_secs}s)"
                    )
                    try:
                        with open(error_log, "a") as f:
                            f.write(
                                f"{datetime.now().isoformat()} @{username} (entry {current})\n"
                            )
                    except Exception:
                        pass

        worker_threads = []
        stop_workers = threading.Event()
        username_iter = iter(usernames)
        iter_lock = threading.Lock()
        print(Fore.GREEN + f"   Starting {threads} workers...", flush=True)

        test_session = requests.Session()
        test_session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        try:
            test_resp = test_session.get("https://www.tiktok.com/@tiktok", timeout=10)
            print(
                Fore.GREEN
                + f"   \u2705 TikTok reachable (status {test_resp.status_code})",
                flush=True,
            )
        except Exception as e:
            print(Fore.RED + f"   \u274c TikTok unreachable: {e}", flush=True)

        def worker_loop(worker_id):
            safe_print(Fore.CYAN + f"   Worker {worker_id} started")
            while (
                not self.claimed
                and not self.stop_scan.is_set()
                and not stop_workers.is_set()
            ):
                with iter_lock:
                    try:
                        username = next(username_iter)
                    except StopIteration:
                        return
                try:
                    check_and_claim(username)
                except Exception as e:
                    safe_print(Fore.RED + f"  \u26a0\ufe0f Worker error: {e}")

        for i in range(threads):
            t = threading.Thread(target=worker_loop, args=(i + 1,))
            t.daemon = True
            t.start()
            worker_threads.append(t)

        try:
            last_progress = time.time()
            last_checked = 0
            while any(t.is_alive() for t in worker_threads):
                time.sleep(1)
                with lock:
                    if (
                        time.time() - last_progress > 60
                        and checked == last_checked
                    ):
                        safe_print(
                            Fore.RED
                            + "\n  \u26a0\ufe0f No progress for 60s \u2014 stopping workers"
                        )
                        stop_workers.set()
                        break
                    last_progress = (
                        time.time() if checked != last_checked else last_progress
                    )
                    last_checked = checked
        except KeyboardInterrupt:
            print("\n\n\U0001f44b Stopped by user")
            stop_workers.set()
            time.sleep(1)

        if not self.claimed:
            print(f"\n{'='*60}")
            print("\U0001f4ca Scan complete - no available usernames claimed")
            print(f"{'='*60}")

    # ── Cleanup ───────────────────────────────────────────────────────────

    def cleanup(self):
        if self.driver:
            print("\n\U0001f9f9 Cleaning up...")
            try:
                self.driver.quit()
                print("   \u2705 Browser closed")
            except Exception:
                pass
