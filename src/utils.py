"""General-purpose utility functions."""

import os
import random
import string
import time

from colorama import Fore
from selenium.webdriver.common.by import By

from src.config import SCRIPT_DIR


def draw_border(text):
    lines = text.strip().split("\n")
    if not lines or not lines[0]:
        lines = [""]
    width = max(len(line) for line in lines) + 4
    print(Fore.CYAN + "\u2554" + "\u2550" * width + "\u2557")
    for line in lines:
        print(Fore.CYAN + "\u2551 " + Fore.WHITE + line.ljust(width - 2) + Fore.CYAN + " \u2551")
    print(Fore.CYAN + "\u255a" + "\u2550" * width + "\u255d")


def random_alphanumeric(length):
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def generate_password(length=12):
    if length < 6:
        length = 6
    if length > 20:
        length = 20
    letters = string.ascii_letters
    digits = string.digits
    special = "!@#$%^&*"
    all_chars = letters + digits + special
    pw = [random.choice(letters), random.choice(digits), random.choice(special)]
    pw += [random.choice(all_chars) for _ in range(length - 3)]
    random.shuffle(pw)
    return "".join(pw)


def select_combobox_value(driver, field_name, value_text):
    combobox = driver.find_element(
        By.XPATH, f"//div[@aria-label='{field_name}. Double-tap for more options']"
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", combobox)
    driver.execute_script("arguments[0].click();", combobox)
    time.sleep(0.3)
    option = driver.find_element(
        By.XPATH, f"//div[@role='option' and text()='{value_text}']"
    )
    driver.execute_script("arguments[0].click();", option)
    time.sleep(0.2)


def save_account(filepath, email, password, created_username="", mail_pass="", birthday=""):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
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
