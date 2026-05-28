#!/usr/bin/env python
# tests/test_bot_mock.py
import unittest
from unittest.mock import MagicMock, patch

# Adjust the import below to point to your bot's entry point.
# If your bot runs from a function called `run` in `bot.py`, change accordingly.
from ticket_bot import main  # <-- import main from ticket_bot.py

class MockWebElement:
    """Simple mock for Selenium WebElement with the methods you use."""
    def __init__(self, text=""):
        self.text = text
        self.clicked = False
        self.sent_keys = ""

    def click(self):
        self.clicked = True

    def send_keys(self, keys):
        self.sent_keys = keys

    def get_attribute(self, name):
        return self.sent_keys if name == "value" else ""

    def clear(self):
        self.sent_keys = ""

    def text(self):
        return self.text

class TestTicketBot(unittest.TestCase):
    @patch("selenium.webdriver.Chrome")
    def test_bot_runs_successfully(self, mock_chrome):
        """Verify the ticket‑bot runs through its workflow without raising exceptions.
        All Selenium interactions are mocked, so no real browser or site is needed.
        """
        # -------------------------------------------------
        # 1️⃣ Configure the mock driver and its page elements
        # -------------------------------------------------
        driver = MagicMock()
        mock_chrome.return_value = driver

        # Mock generic element look‑ups used by the bot.
        driver.find_element.return_value = MockWebElement()
        driver.find_elements.return_value = [MockWebElement()]

        # Patch WebDriverWait to return immediately if used.
        wait_patch = patch("ticket_bot.WebDriverWait")
        mock_wait = wait_patch.start()
        mock_wait.return_value.until.return_value = MockWebElement()

        # -------------------------------------------------
        # 2️⃣ Run the bot with load_config patched
        # -------------------------------------------------
        # Provide a minimal config so the bot doesn’t try to read a real yaml file.
        dummy_cfg = {
            "headless": True,
            "event_url": "https://example.com/event",
            "username": "user",
            "password": "pass",
            "login_url": "https://example.com/login",
        }
        with patch("ticket_bot.load_config", return_value=dummy_cfg):
            try:
                main()
            except Exception as exc:
                self.fail(f"Bot raised an exception under mock conditions: {exc}")
        # -------------------------------------------------
        # 3️⃣ Basic sanity checks (optional)
        # -------------------------------------------------
        mock_chrome.assert_called_once()
        driver.quit.assert_called_once()

        # Clean up the wait patch
        wait_patch.stop()

if __name__ == "__main__":
    unittest.main()
