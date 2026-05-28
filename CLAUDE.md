# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---  

## Common Development Commands  

| Task | Command | Notes |
|------|---------|-------|
| Install dependencies | `pip install -r requirements.txt` | Uses the *requirements.txt* file (Selenium, PyYAML). |
| Run the bot (full flow) | `python ticket_bot.py` | Executes the main entry‑point defined in `ticket_bot.py`. |
| Run **all** tests | `pytest` | Test suite lives under the `tests/` directory. |
| Run a **single** test file | `pytest tests/test_bot_mock.py` | Replace the path with the desired test file. |
| Run a **single** test case | `pytest tests/test_bot_mock.py::test_login_flow` | Append `::test_name` to the file path. |
| Lint / static check | *(no dedicated linter configured – install one locally if needed)* | Add a linter command here if one is added later. |
| Re‑run a failed test quickly | `pytest -x` | Stops after the first failure. |
| Clean virtual‑env (re‑create) | `rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` | Useful when dependency issues arise. |

*All commands assume you are at the repository root (`/Users/shmunky/striker`).*

---  

## High‑Level Architecture  

```
repo/
├─ README.md                     ← Overview, setup, usage
├─ requirements.txt              ← Python dependencies
├─ config.yaml                   ← Runtime configuration (URLs, selectors, flags)
├─ ticket_bot.py                 ← Core automation script
├─ tests/
│   ├─ test_bot_comprehensive.py ← End‑to‑end integration style tests
│   ├─ test_bot_mock.py          ← Mock‑based unit tests (no real browser)
│   ├─ inspect_login_modal.py    ← Helper for inspecting the login modal UI
│   └─ inspect_page.py           ← Helper for page‑inspection utilities
└─ venv/                         ← Local virtual environment (not version‑controlled)
```

### `ticket_bot.py` – Main Engine  

1. **Configuration loading** – `load_config()` reads *config.yaml* (YAML).  
2. **WebDriver initialization** – `init_driver(headless)` builds a Chrome driver with stealth options to evade bot detection (disables automation flags, injects JS to hide `navigator.webdriver`).  
3. **Cookie consent handling** – `dismiss_cookie_consent()` iterates a large list of CSS selectors and XPath expressions (including Thai language keywords) to click “Accept” buttons safely.  
4. **Login flow** – `login_if_needed()` navigates to the login URL, dismisses cookies, clicks the login trigger (fallback selector from config), then clicks the Google/Gmail button and waits until the login button disappears.  
5. **Ticket purchase** – `purchase_ticket()` opens the event page, dismisses cookies, clicks the buy button (configurable selector), optional confirmation step, waits for a success message, and optionally extracts an order number.  
6. **Entry point** – `main()` glues the above steps, respecting the `headless` flag from the config and ensuring driver shutdown via a `finally` block.

### Test Suite  

- **Mock‑based tests** (`test_bot_mock.py`) use Selenium “mocks” to exercise the flow without launching a real browser, enabling fast CI feedback.  
- **Comprehensive integration tests** (`test_bot_comprehensive.py`) may launch a real ChromeDriver (requires ChromeDriver in `$PATH`).  
- Helper modules under `tests/` provide reusable inspection utilities for modal dialogs and generic page elements.

### Configuration (`config.yaml`)  

Key entries used by the bot:

| Key | Purpose |
|-----|---------|
| `login_url` / `event_url` | Base URLs for login and ticket pages. |
| `headless` | Boolean – run Chrome in headless mode. |
| `buy_button_selector` | CSS selector for the ticket “Buy” button (default `button[data-action='buy']`). |
| `confirm_button_selector` | Optional selector for an extra confirmation step. |
| `success_message_xpath` | XPath used to detect successful purchase. |
| `order_number_selector` | Optional CSS selector to pull the order reference. |
| `login_trigger_selector` | Fallback selector if the primary login button selector changes. |

Add or modify selectors in *config.yaml* to adapt to UI changes without touching code.

---  

## Development Tips (specific to this repo)  

- **Headless vs. headed** – The default in `config.yaml` is `headless: true`. Set it to `false` for visual debugging.  
- **Cookie handling** – The bot maintains a long selector list to cope with multiple UI languages; extending this list is preferred over editing the click logic.  
- **Stealth options** – The driver disables `AutomationControlled` and removes the `webdriver` flag; keep these lines unless a site explicitly blocks them.  
- **Test isolation** – Mock tests do not require ChromeDriver; they are the fastest way to verify logic changes. Only run the comprehensive suite when you need to validate against a real browser.  

---  

*If a `CLAUDE.md` already exists, incorporate these sections and remove any duplicated or outdated instructions.*