# CPZC Auto Claimer

TikTok username auto-claimer with a modern GUI. Scans thousands of usernames via HTTP requests and automatically claims available ones through Selenium browser automation.

## Features

- **Modern GUI** — customtkinter-based interface with sidebar navigation, dark theme, and responsive layout
- **Multi-threaded scanning** — checks thousands of usernames concurrently via HTTP requests
- **Automated claiming** — detects available usernames and claims them through Selenium
- **Automated login** — handles email/password login with verification code auto-retrieval from FirstMail
- **CAPTCHA notifications** — sends Discord/Telegram alerts when manual CAPTCHA solving is required
- **Theme system** — 5 built-in presets (Midnight, Ocean, Forest, Sunset, Purple Haze) + full custom color editor
- **Accounts manager** — view and login to saved accounts directly from the GUI
- **Username generator** — generate random usernames with configurable charset, length, and prefix
- **Cookie management** — save and load browser sessions

## Requirements

- Python 3.8+
- Google Chrome or Chromium installed

## Installation

```bash
git clone https://github.com/cpzc/cpzc-auto-claimer.git
cd cpzc-auto-claimer
pip install -r requirements.txt
```

## Usage

```bash
python app.py
```

### Data Files

Place your data in the `data/` directory:

| File | Format | Description |
|------|--------|-------------|
| `usernames.txt` | One per line | Usernames to scan |
| `accounts.txt` | `username:password:email:emailpass` | Account credentials for login |
| `sessions.txt` | Chrome cookies JSON | Saved browser sessions |

## Configuration

Edit `config.json` to configure notifications, delays, and theme:

```json
{
  "discord_webhook_url": "",
  "telegram_bot_token": "",
  "telegram_chat_id": "",
  "username_input_delay": 2,
  "headless": false,
  "theme": "midnight"
}
```

## How It Works

1. **Scan** — Worker threads check usernames against TikTok's API via HTTP requests (404 = available)
2. **Claim** — Available usernames are claimed through a Selenium browser session on the Edit Profile page
3. **Verify** — If TikTok triggers "Verify it's really you", the tool auto-retrieves verification codes from FirstMail
4. **Notify** — Success and CAPTCHA alerts are sent to Discord/Telegram

## License

MIT
