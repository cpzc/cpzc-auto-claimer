"""TikTok account creation with temporary email verification."""

import os
import re
import time

import requests
from colorama import Fore
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from src.config import SCRIPT_DIR
from src.utils import (
    generate_password,
    random_alphanumeric,
    select_combobox_value,
    save_account,
    check_rate_limited,
)


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
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
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
            },
        )
    except Exception:
        pass

    wait = WebDriverWait(driver, 20)
    rngpassword = generate_password(12)
    auto_email = True
    url = "https://www.tiktok.com/signup/phone-or-email/email"

    try:
        driver.get(url)
        time.sleep(2)

        try:
            lang_select = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "select[class*='SelectFormContainer']")
                )
            )
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
            requests.post(
                "https://api.mail.tm/accounts",
                json={"address": email_addr, "password": email_pass},
                timeout=10,
            )
            token_resp = requests.post(
                "https://api.mail.tm/token",
                json={"address": email_addr, "password": email_pass},
                timeout=10,
            )
            mail_token = token_resp.json()["token"]
            email_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[name="email"]')
                )
            )
            email_input.send_keys(email_addr)
        except Exception as e:
            auto_email = False
            email = input_fn("Enter your Email: ")
            email_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[name="email"]')
                )
            )
            email_input.send_keys(email)
            email_addr = email
        time.sleep(0.3)

        driver.find_element(By.CSS_SELECTOR, 'input[type="password"]').send_keys(
            rngpassword
        )
        time.sleep(0.3)

        try:
            cb = driver.find_element(By.CSS_SELECTOR, "input#email-consent")
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
                btn = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'button[data-e2e="send-code-button"]')
                    )
                )
                driver.execute_script("arguments[0].click();", btn)
            except Exception:
                try:
                    btn = driver.find_element(
                        By.CSS_SELECTOR, 'button[type="submit"]'
                    )
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
                        msg_resp = requests.get(
                            "https://api.mail.tm/messages",
                            headers=headers,
                            timeout=5,
                        )
                        msgs = msg_resp.json().get("hydra:member", [])
                        if msgs:
                            detail = requests.get(
                                f"https://api.mail.tm/messages/{msgs[0]['id']}",
                                headers=headers,
                                timeout=5,
                            ).json()
                            body = detail.get("text", "") or detail.get("html", "")
                            match = re.search(r"(\d{6})", body)
                            if match:
                                get_code = match.group(1)
                                break
                        time.sleep(3)
                    except Exception:
                        time.sleep(3)

                if get_code:
                    code_input = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.CSS_SELECTOR,
                                'input[placeholder="Enter 6-digit code"]',
                            )
                        )
                    )
                    code_input.send_keys(get_code)
                    break
                else:
                    if attempt < 2:
                        driver.refresh()
                        time.sleep(2)
                        try:
                            lang_select = wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.CSS_SELECTOR,
                                        "select[class*='SelectFormContainer']",
                                    )
                                )
                            )
                            Select(lang_select).select_by_value("en")
                        except Exception:
                            pass
                        time.sleep(0.3)
                        select_combobox_value(driver, "Month", "January")
                        select_combobox_value(driver, "Day", "1")
                        select_combobox_value(driver, "Year", "2000")
                        time.sleep(0.3)
                        if auto_email:
                            email_input = wait.until(
                                EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, 'input[name="email"]')
                                )
                            )
                            email_input.send_keys(email_addr)
                            driver.find_element(
                                By.CSS_SELECTOR, 'input[type="password"]'
                            ).send_keys(rngpassword)
                    else:
                        if own_driver:
                            driver.quit()
                        else:
                            pause_fn("Press Enter to return to login...")
                        return False
            else:
                code = input_fn("Enter Code from Email: ")
                code_input = wait.until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            'input[placeholder="Enter 6-digit code"]',
                        )
                    )
                )
                code_input.send_keys(code)
                break

        time.sleep(2)

        if check_rate_limited(driver):
            return False

        try:
            next_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[normalize-space()='Next']")
                )
            )
            next_btn.click()
            time.sleep(3)
        except Exception:
            pass

        if check_rate_limited(driver):
            return False

        birthday_str = "January 1, 2000"
        save_account(
            os.path.join(SCRIPT_DIR, "data", "created_accounts.csv"),
            email_addr,
            rngpassword,
            "",
            email_pass if auto_email else "",
            birthday_str,
        )

        if own_driver:
            pause_fn("Press Enter to return...")

        return True
    except Exception as e:
        print(Fore.RED + f"Error: {e}")
        return False
    finally:
        if own_driver:
            driver.quit()
