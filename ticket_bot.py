import os
import time
import logging
import yaml
from typing import Dict, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
)

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Configuration – edit config.yaml to change values
# ------------------------------------------------------------------
CONFIG_PATH = "config.yaml"

REQUIRED_CONFIG_KEYS = ["event_url", "login_url"]


def load_config(path: str) -> Dict[str, Any]:
    """Load and validate configuration from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Validate required keys
    missing = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg or not cfg[k]]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    # Override credentials from environment if set
    cfg.setdefault("username", os.environ.get("TICKET_USERNAME", ""))
    cfg.setdefault("password", os.environ.get("TICKET_PASSWORD", ""))

    return cfg


def init_driver(headless: bool) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--start-maximized")

    # Add stealth arguments to bypass Cloudflare / Anti-bot detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # Hide webdriver flag via JavaScript execution on page load
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )

    driver.maximize_window()
    return driver


def dismiss_cookie_consent(driver: webdriver.Remote) -> bool:
    logger.info("Looking for cookie consent banner to agree...")
    cookie_selectors = [
        "button.btn.leave",
        "button.leave",
        "button#accept-cookie",
        "button.accept-cookie",
        "button[id*='cookie']",
        "button[class*='cookie']",
        "a[class*='cookie']",
        "[id*='cookie'] a",
        "[id*='cookie'] button",
        "[class*='cookie'] button",
        "[class*='cookie'] a",
        "[id*='consent'] button",
        "[class*='consent'] button",
        "button[class*='btn-accept']",
        "button[class*='accept']",
        "button[class*='agree']",
        "a[class*='accept']",
        "a[class*='agree']",
        ".cookie-banner button",
        ".cookie-box button",
        "#cookie-banner button",
        "#cookie-box button",
        ".cc-btn.cc-dismiss",
        ".cc-accept-all",
        "button.agree-button",
        "button.btn-primary",
    ]

    def try_click_element(el):
        try:
            el.click()
            return True
        except ElementClickInterceptedException:
            try:
                logger.warning("Standard click failed. Attempting JavaScript click...")
                driver.execute_script("arguments[0].click();", el)
                return True
            except WebDriverException as js_err:
                logger.warning("JavaScript click also failed: %s", js_err)
                return False

    # Try finding by CSS selector first
    for selector in cookie_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                element_text = element.text.lower()
                is_displayed = element.is_displayed()
                is_enabled = element.is_enabled()

                if is_displayed and is_enabled:
                    is_specific = selector in ["button.btn.leave", "button.leave"]
                    thai_keywords = ["ยอมรับ", "ตกลง", "ยินยอม", "บันทึก"]
                    if (
                        is_specific
                        or any(kw in element_text for kw in ["accept", "allow", "agree", "ok"])
                        or any(kw in element.text for kw in thai_keywords)
                    ):
                        logger.info(
                            "Clicking cookie accept button using selector: %s (text: '%s')",
                            selector,
                            element_text,
                        )
                        if try_click_element(element):
                            logger.debug("Waiting for cookie banner to settle...")
                            return True
        except WebDriverException:
            pass

    # Try finding by XPath with text content
    xpath_templates = [
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'accept')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'allow')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'agree')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'ok')]",
        "//*[contains(text(), 'ยอมรับ')]",
        "//*[contains(text(), 'ตกลง')]",
        "//*[contains(text(), 'ยินยอม')]",
        "//*[contains(text(), 'บันทึก')]",
    ]

    for xpath in xpath_templates:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                tag_name = element.tag_name.lower()
                is_displayed = element.is_displayed()
                is_enabled = element.is_enabled()

                if tag_name in ["button", "a", "div", "span"] and is_displayed and is_enabled:
                    element_text = element.text
                    logger.info(
                        "Clicking cookie accept button using XPath: %s (tag: %s, text: '%s')",
                        xpath,
                        tag_name,
                        element_text,
                    )
                    if try_click_element(element):
                        import time
                        time.sleep(1.5)
                        return True
        except WebDriverException:
            pass

    logger.info("No visible cookie banner / accept button found or already dismissed.")
    return False


def login_if_needed(driver: webdriver.Remote, cfg: Dict[str, Any]) -> None:
    login_url = cfg.get("login_url", cfg["event_url"]).strip()
    driver.get(login_url)
    dismiss_cookie_consent(driver)
    wait = WebDriverWait(driver, 15)

    # 1. Open the login modal by clicking the login button
    try:
        logger.info("Clicking login trigger button (button.login-btn)...")
        trigger_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login-btn"))
        )
        try:
            trigger_btn.click()
        except ElementClickInterceptedException:
            logger.warning("Standard click on login trigger failed. Attempting JS click...")
            driver.execute_script("arguments[0].click();", trigger_btn)
    except TimeoutException as e:
        trigger_sel = cfg.get("login_trigger_selector")
        if trigger_sel:
            try:
                logger.info("Clicking fallback login trigger: %s", trigger_sel)
                trigger_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, trigger_sel))
                )
                try:
                    trigger_btn.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", trigger_btn)
            except TimeoutException as ex:
                logger.warning("Could not click fallback login trigger: %s", ex)
        else:
            logger.warning("Could not click login button: %s", e)

    # 2. Click the Google/Gmail login button
    logger.info("Looking for Gmail/Google login button (button.btn-google)...")
    google_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-google"))
    )
    logger.info("Clicking Gmail/Google login button...")
    try:
        google_btn.click()
    except ElementClickInterceptedException:
        logger.warning("Standard click on Google button failed. Attempting JS click...")
        driver.execute_script("arguments[0].click();", google_btn)

    # 3. Wait for the login to complete
    logger.info(
        "Waiting for Gmail/Google login to complete. "
        "Please complete login in the Chrome window if prompted..."
    )

    def is_logged_in(d):
        try:
            elements = d.find_elements(By.CSS_SELECTOR, "button.login-btn")
            if not elements:
                return True
            btn = elements[0]
            if btn is None:
                return True
            return not btn.is_displayed()
        except WebDriverException:
            return False

    login_wait = WebDriverWait(driver, 120)
    login_wait.until(is_logged_in)
    logger.info("Successfully logged in via Gmail/Google!")


def purchase_ticket(driver: webdriver.Remote, cfg: Dict[str, Any]) -> None:
    driver.get(cfg["event_url"].strip())
    dismiss_cookie_consent(driver)
    wait = WebDriverWait(driver, 20)

    # Click the buy button
    buy_selector = cfg.get("buy_button_selector", "button[data-action='buy']")
    for attempt in range(3):
        try:
            buy_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, buy_selector)))
            buy_btn.click()
            break
        except (ElementClickInterceptedException, StaleElementReferenceException):
            if attempt == 2:
                raise
            time.sleep(1)

    # Optional confirm step
    confirm_selector = cfg.get("confirm_button_selector")
    if confirm_selector:
        try:
            confirm_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, confirm_selector))
            )
            confirm_btn.click()
        except (TimeoutException, NoSuchElementException):
            pass  # if not present, continue

    # Wait for success message
    success_xpath = cfg.get(
        "success_message_xpath", "//h1[contains(text(),'Thank you')]"
    )
    wait.until(EC.presence_of_element_located((By.XPATH, success_xpath)))
    logger.info("Ticket purchase completed successfully.")

    # Capture order number if possible
    order_sel = cfg.get("order_number_selector")
    if order_sel:
        try:
            order_el = driver.find_element(By.CSS_SELECTOR, order_sel)
            logger.info("Order number: %s", order_el.text)
        except NoSuchElementException:
            pass


def main() -> None:
    cfg = load_config(CONFIG_PATH)
    driver = init_driver(cfg.get("headless", True))
    try:
        login_if_needed(driver, cfg)
        purchase_ticket(driver, cfg)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()