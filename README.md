<div align="center">

# CPZC Auto Claimer

**TikTok username auto-claimer with a modern GUI**

Scans thousands of usernames via HTTP requests and automatically claims available ones through Selenium browser automation.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## Features

- **Multi-threaded scanning** — checks thousands of usernames concurrently
- **Automated claiming** — claims available usernames via Selenium
- **Modern GUI** — customtkinter with dark theme
- **5 theme presets** — Midnight, Ocean, Forest, Sunset, Purple Haze + custom colors
- **Accounts manager** — view and login saved accounts from the GUI
- **Username generator** — random name generation with configurable charset
- **Discord/Telegram notifications** — claim success and CAPTCHA alerts

---

## Quick Start

```bash
git clone https://github.com/cpzc/cpzc-auto-claimer.git
cd cpzc-auto-claimer
pip install -r requirements.txt
python app.py
```

---

## Data Files

Place your data in the `data/` directory:

| File | Format | Description |
|:-----|:-------|:------------|
| `usernames.txt` | One per line | Usernames to scan |
| `accounts.txt` | `username:password:email:emailpass` | Account credentials |
| `sessions.txt` | Chrome cookies JSON | Saved browser sessions |

---

## Configuration

Edit `config.json` to set up notifications and preferences:

```json
{
  "discord_webhook_url": "",
  "telegram_bot_token": "",
  "telegram_chat_id": "",
  "username_input_delay": 2,
  "headless": false,
  "theme": "Sunset"
}
```

---

## License

[MIT](LICENSE)
