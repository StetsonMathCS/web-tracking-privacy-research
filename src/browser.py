"""Chrome browser creation and clean-session management."""

import shutil
import tempfile
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(
    headless: bool = True,
    page_load_timeout: int = 30,
    performance_logging: bool = True,
):
    """
    Start a new Chrome session with a unique temporary profile.

    A new user-data directory is created for every attempt. This isolates
    cookies, local storage, cache, and other browser state between websites.
    The caller must call driver.quit() and remove driver._profile_dir.
    """
    profile_dir = Path(tempfile.mkdtemp(prefix="website_test_chrome_"))
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-data-dir={profile_dir}")

   # options.add_argument("--no-sandbox")

    if performance_logging:
        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL"},
        )

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(page_load_timeout)
        driver._profile_dir = str(profile_dir)

        if performance_logging:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Page.enable", {})

        return driver

    except Exception:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        shutil.rmtree(profile_dir, ignore_errors=True)
        raise


def close_driver(driver):
    """Close Chrome and remove its temporary profile."""
    if driver is None:
        return

    profile_dir = getattr(driver, "_profile_dir", None)

    try:
        driver.quit()
    finally:
        if profile_dir:
            shutil.rmtree(profile_dir, ignore_errors=True)
