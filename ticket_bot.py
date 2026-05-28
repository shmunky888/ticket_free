import time
import yaml
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------------------------------------------------------
# Configuration – edit config.yaml to change values
# ------------------------------------------------------------------
CONFIG_PATH = "config.yaml"

def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def init_driver(headless: bool):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1920, 1080)
    return driver


def login_if_needed(driver, cfg):
    if not cfg.get("username"):
        return
    login_url = cfg.get("login_url", cfg["event_url"]).strip()
    driver.get(login_url)
    wait = WebDriverWait(driver, 15)
    # try common field selectors
    try:
        username_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
    except Exception:
        username_field = wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
    password_field = driver.find_element(By.NAME, "password")
    username_field.clear()
    username_field.send_keys(cfg["username"])
    password_field.clear()
    password_field.send_keys(cfg["password"])
    # submit – try common button types
    try:
        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    except Exception:
        submit = driver.find_element(By.XPATH, "//input[@type='submit']")
    submit.click()
    # wait for post‑login navigation (adjust as needed)
    wait.until(lambda d: cfg.get("post_login_url_fragment", "dashboard") in d.current_url)


def purchase_ticket(driver, cfg):
    driver.get(cfg["event_url"].strip())
    wait = WebDriverWait(driver, 20)
    # Click the buy button
    buy_selector = cfg.get("buy_button_selector", "button[data-action='buy']")
    buy_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, buy_selector)))
    for attempt in range(3):
        try:
            buy_btn.click()
            break
        except Exception as e:
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
        except Exception:
            pass  # if not present, continue
    # Wait for success message
    success_xpath = cfg.get(
        "success_message_xpath", "//h1[contains(text(),'Thank you')]"
    )
    wait.until(EC.presence_of_element_located((By.XPATH, success_xpath)))
    print("✅ Ticket purchase completed successfully.")
    # Capture order number if possible
    order_sel = cfg.get("order_number_selector")
    if order_sel:
        try:
            order_el = driver.find_element(By.CSS_SELECTOR, order_sel)
            print("Order number:", order_el.text)
        except Exception:
            pass


def main():
    cfg = load_config(CONFIG_PATH)
    driver = init_driver(cfg.get("headless", True))
    try:
        login_if_needed(driver, cfg)
        purchase_ticket(driver, cfg)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
