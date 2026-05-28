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
    options.add_argument("--start-maximized")
    
    # Add stealth arguments to bypass Cloudflare / Anti-bot detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    driver = webdriver.Chrome(options=options)
    
    # Hide webdriver flag via JavaScript execution on page load
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    
    driver.maximize_window()
    return driver


def dismiss_cookie_consent(driver):
    print("🔍 Looking for cookie consent banner to agree...")
    # List of common selectors for cookie accept buttons
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
        "button.btn-primary"
    ]
    
    def try_click_element(el, method_desc):
        try:
            el.click()
            return True
        except Exception as e:
            try:
                print(f"⚠️ Standard click failed ({e}). Attempting JavaScript click...")
                driver.execute_script("arguments[0].click();", el)
                return True
            except Exception as js_err:
                print(f"⚠️ JavaScript click also failed: {js_err}")
                return False

    # Try finding by CSS selector first
    for selector in cookie_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                # Retrieve text safely (handles string vs method in mocks)
                element_text = ""
                if hasattr(element, "text"):
                    element_text = element.text
                    if callable(element_text):
                        element_text = element_text()
                text = element_text.lower()
                
                # Check displayed and enabled status safely
                is_displayed = True
                if hasattr(element, "is_displayed"):
                    is_displayed = element.is_displayed()
                is_enabled = True
                if hasattr(element, "is_enabled"):
                    is_enabled = element.is_enabled()
                
                if is_displayed and is_enabled:
                    is_specific = selector in ["button.btn.leave", "button.leave"]
                    if is_specific or any(kw in text for kw in ["accept", "allow", "agree", "ok", "ตกลง", "ยอมรับ", "ยินยอม", "yes"]):
                        print(f"Clicking cookie accept button using selector: {selector} (text: '{element_text}')")
                        if try_click_element(element, f"selector: {selector}"):
                            time.sleep(1.5)
                            return True
        except Exception:
            pass

    # Try finding by XPath with text content (case-insensitive for English, direct match for Thai)
    xpath_templates = [
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'accept')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'allow')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'agree')]",
        "//*[contains(translate(text(), 'ACCEPTALLOWGREE', 'acceptallowgree'), 'ok')]",
        "//*[contains(text(), 'ยอมรับ')]",
        "//*[contains(text(), 'ตกลง')]",
        "//*[contains(text(), 'ยินยอม')]",
        "//*[contains(text(), 'บันทึก')]"
    ]
    
    for xpath in xpath_templates:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for element in elements:
                # Retrieve tag name safely
                tag_name = "button"
                if hasattr(element, "tag_name"):
                    tag_name = element.tag_name
                    if callable(tag_name):
                        tag_name = tag_name()
                tag_name = tag_name.lower()
                
                # Retrieve displayed and enabled status safely
                is_displayed = True
                if hasattr(element, "is_displayed"):
                    is_displayed = element.is_displayed()
                is_enabled = True
                if hasattr(element, "is_enabled"):
                    is_enabled = element.is_enabled()
                
                if tag_name in ["button", "a", "div", "span"] and is_displayed and is_enabled:
                    element_text = ""
                    if hasattr(element, "text"):
                        element_text = element.text
                        if callable(element_text):
                            element_text = element_text()
                    print(f"Clicking cookie accept button using XPath: {xpath} (tag: {tag_name}, text: '{element_text}')")
                    if try_click_element(element, f"XPath: {xpath}"):
                        time.sleep(1.5)
                        return True
        except Exception:
            pass
            
    print("No visible cookie banner / accept button found or already dismissed.")
    return False



def login_if_needed(driver, cfg):
    login_url = cfg.get("login_url", cfg["event_url"]).strip()
    driver.get(login_url)
    dismiss_cookie_consent(driver)
    wait = WebDriverWait(driver, 15)
    
    # 1. Open the login modal by clicking the login button
    try:
        print("🔍 Clicking login trigger button (button.login-btn)...")
        trigger_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.login-btn"))
        )
        try:
            trigger_btn.click()
        except Exception:
            print("⚠️ Standard click on login trigger failed/intercepted. Attempting JS click...")
            driver.execute_script("arguments[0].click();", trigger_btn)
        time.sleep(1.5)
    except Exception as e:
        trigger_sel = cfg.get("login_trigger_selector")
        if trigger_sel:
            try:
                print(f"🔍 Clicking fallback login trigger: {trigger_sel}")
                trigger_btn = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, trigger_sel))
                )
                try:
                    trigger_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", trigger_btn)
                time.sleep(1.5)
            except Exception as ex:
                print(f"⚠️ Could not click fallback login trigger: {ex}")
        else:
            print(f"⚠️ Could not click login button: {e}")
            
    # 2. Click the Google/Gmail login button
    print("🔍 Looking for Gmail/Google login button (button.btn-google)...")
    google_btn = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-google"))
    )
    print("🚀 Clicking Gmail/Google login button...")
    try:
        google_btn.click()
    except Exception:
        print("⚠️ Standard click on Google button failed/intercepted. Attempting JS click...")
        driver.execute_script("arguments[0].click();", google_btn)
    
    # 3. Wait for the login to complete (either automatically or with manual account selection/MFA)
    print("⏳ Waiting for Gmail/Google login to complete. Please complete login in the Chrome window if prompted...")
    
    def is_logged_in(d):
        try:
            # If the login button is no longer present or visible, we are logged in!
            # Using find_elements prevents throwing Exceptions if not found, and works cleanly with mocks
            elements = d.find_elements(By.CSS_SELECTOR, "button.login-btn")
            if not elements:
                return True
            btn = elements[0]
            if btn is None:
                return True
            return not btn.is_displayed()
        except Exception:
            return True
            
    login_wait = WebDriverWait(driver, 120)
    login_wait.until(is_logged_in)
    print("✅ Successfully logged in via Gmail/Google!")



def purchase_ticket(driver, cfg):
    driver.get(cfg["event_url"].strip())
    dismiss_cookie_consent(driver)
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
