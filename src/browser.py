from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless: bool = True) -> webdriver.Chrome:
    """Create a fresh Chrome session for one attempt."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--incognito")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-background-networking")
    options.add_argument("--window-size=1440,1000")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)
