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
| Re‑run a failed test quickly | `pytest -x` | Stops after the first failure. |
| Clean virtual‑env (re‑create) | `rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` | Useful when dependency issues arise. |

*All commands assume you are at the repository root (`/Users/shmunky/striker`).*

**Prerequisites:** Python 3.10+, ChromeDriver in `$PATH`, and a Google/Gmail account for login.

---

## High-Level Architecture

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
3. **Cookie consent handling** – `dismiss_cookie_consent()` iterates a large list of CSS selectors and XPath expressions (including Thai language keywords) to click "Accept" buttons safely.
4. **Login flow** – `login_if_needed()` navigates to the login URL, dismisses cookies, clicks the login trigger (fallback selector from config), then clicks the Google/Gmail button and waits until the login button disappears.
5. **Ticket purchase** – `purchase_ticket()` opens the event page, dismisses cookies, clicks the buy button (configurable selector), optional confirmation step, waits for a success message, and optionally extracts an order number.
6. **Entry point** – `main()` glues the above steps, respecting the `headless` flag from the config and ensuring driver shutdown via a `finally` block.

### Test Suite

- **Mock‑based tests** (`tests/test_bot_mock.py`) use Selenium mocks to exercise the flow without launching a real browser, enabling fast CI feedback.
- **Comprehensive integration tests** (`tests/test_bot_comprehensive.py`) may launch a real ChromeDriver and navigate the actual site.
- **Helper modules** (`tests/inspect_login_modal.py`, `tests/inspect_page.py`) provide utilities for debugging UI elements during development.

### Configuration

Use `config.yaml` for runtime settings. A template is available as `config.example.yaml`. Key entries:

| Key | Purpose |
|-----|---------|
| `event_url` / `login_url` | URLs for ticket page and login page. |
| `headless` | `true` for headless mode, `false` for visible browser. |
| `buy_button_selector` | CSS selector for the ticket "Buy" button. |
| `confirm_button_selector` | Optional selector for extra confirmation step. |
| `success_message_xpath` | XPath to detect successful purchase. |
| `order_number_selector` | Optional selector to extract order reference. |
| `login_trigger_selector` | Fallback selector for the login modal trigger. |

Set `username`/`password` via `TICKET_USERNAME` and `TICKET_PASSWORD` environment variables.

---

## Development Tips

- **Headless vs. headed** – Set `headless: false` in `config.yaml` for visual debugging.
- **Cookie handling** – Extend the selector list in `dismiss_cookie_consent()` rather than modifying click logic.
- **Stealth options** – Keep automation flag disabling unless the site explicitly blocks them.
- **Test isolation** – Mock tests (`pytest tests/test_bot_mock.py`) verify logic without ChromeDriver. Run comprehensive tests only for browser validation.