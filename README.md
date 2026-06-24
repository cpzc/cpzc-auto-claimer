<div align="center">

# CPZC Auto Claimer

**TikTok username auto-claimer with a modern GUI**

Scans thousands of usernames via HTTP requests and automatically claims available ones through Selenium browser automation.

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Selenium](https://img.shields.io/badge/Selenium-4.x-43B02A?style=for-the-badge&logo=selenium&logoColor=white)](https://www.selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/cpzc/cpzc-auto-claimer?style=for-the-badge&color=orange)](https://github.com/cpzc/cpzc-auto-claimer/stargazers)

</div>

---

## Features

<table>
<tr>
<td width="50%">

### Core
- **Multi-threaded scanning** — checks thousands of usernames concurrently
- **Automated claiming** — claims available usernames via Selenium
- **Automated login** — handles verification codes from FirstMail
- **CAPTCHA alerts** — Discord/Telegram notifications

</td>
<td width="50%">

### GUI
- **Modern interface** — customtkinter with dark theme
- **5 theme presets** — Midnight, Ocean, Forest, Sunset, Purple Haze
- **Custom colors** — full color editor with live preview
- **Accounts manager** — view/login saved accounts
- **Username generator** — random name generation

</td>
</tr>
</table>

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/cpzc/cpzc-auto-claimer.git
cd cpzc-auto-claimer
pip install -r requirements.txt
```

### 2. Run

```bash
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
  "discord_webhook_url": "YOUR_WEBHOOK_URL",
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "username_input_delay": 2,
  "headless": false,
  "theme": "Sunset"
}
```

| Setting | Description |
|:--------|:------------|
| `discord_webhook_url` | Discord webhook for claim/CAPTCHA notifications |
| `telegram_bot_token` | Telegram bot token for notifications |
| `telegram_chat_id` | Telegram chat ID for notifications |
| `username_input_delay` | Delay (seconds) between username input attempts |
| `headless` | Run browser in headless mode |
| `theme` | GUI theme preset name |

---

## How It Works

```
  Scan                    Claim                   Verify
┌─────────┐           ┌──────────┐           ┌──────────┐
│  HTTP   │   404     │ Selenium │  CAPTCHA   │ FirstMail│
│  Check  │ ───────>  │  Browser │ ────────>  │  Inbox   │
│  (x N)  │ available │  Action  │  detected  │  Auto    │
└─────────┘           └──────────┘           └──────────┘
     │                      │                      │
     └──────────────────────┴──────────────────────┘
                    Discord / Telegram
                    Notification sent
```

1. **Scan** — Worker threads check usernames via HTTP (404 = available)
2. **Claim** — Available usernames are claimed through Selenium on the Edit Profile page
3. **Verify** — If TikTok triggers "Verify it's really you", codes are auto-retrieved from FirstMail
4. **Notify** — Success and CAPTCHA alerts are sent to Discord/Telegram

---

## Supported Email Providers

Only **FirstMail** domains are supported for automatic verification:

> `firstmail.ltd` · `firstmail.online` · `firstmailler.com` · `firstmailler.net` · `raymanmail.com` · `fmaild.com` · `dfirstmail.com` · `tformemail.com` · `mergencmail.com` · `protecemail.com` · `ervmail.com` · `espismail.com` · `spitalitmail.com` · `maillsk.com` · `maillv.com` · `oonmail.com` · `znemail.com` · `sabesmail.com` · `bonjourfmail.com` · `reevalmail.com` · `bientotmail.com`

---

## License

[MIT](LICENSE)
