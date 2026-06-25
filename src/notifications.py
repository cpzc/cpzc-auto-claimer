"""Discord and Telegram notification functions."""

import requests
from colorama import Fore


def send_claim_notification(username, config):
    profile_url = f"https://www.tiktok.com/@{username}"
    message = f"\U0001f389 Claimed @{username}!\n\U0001f517 {profile_url}"
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
