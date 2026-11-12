"""Retry one website independently and log only its final failure."""

import csv
import time
from datetime import datetime
from pathlib import Path

from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.support.ui import WebDriverWait

from analyzer import extract_measurements
from browser import create_driver, close_driver
from fingerprint_analyzer import install_fingerprinting_monitor

ERROR_COLUMNS = [
    "Timestamp",
    "URL",
    "Category",
    "Region",
    "Attempt Count",
    "Error Type",
    "Error Message",
]
def _append_error(error_log_path, row):
    """Append a failure row and create the CSV header when needed."""
    path = Path(error_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    write_header = not path.exists() or path.stat().st_size == 0

    if not write_header:
        with path.open("r", newline="", encoding="utf-8-sig") as file:
            existing_header = next(csv.reader(file), [])

        if existing_header != ERROR_COLUMNS:
            raise ValueError(
                f"{path} has an older/different header. "
                f"Expected {ERROR_COLUMNS}, found {existing_header}. "
                "Rename or back up the old file before running this version."
            )

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=ERROR_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_website_with_retries(
    url,
    category,
    region,
    error_log_path,
    max_attempts=3,
    headless=True,
    page_load_timeout=30,
    settle_seconds=6,
    analyze_fingerprinting=True,
    save_failure_screenshot=False,
    screenshot_dir=None,
):
    """
    Try one website up to max_attempts times.

    Every attempt gets a brand-new Chrome session and temporary profile.
    Cookie banners are deliberately not accepted automatically.
    """
    last_error = None

    for attempt in range(1, max_attempts + 1):
        driver = None

        try:
            print(f"Attempt {attempt}/{max_attempts}: {url}")

            driver = create_driver(
                headless=headless,
                page_load_timeout=page_load_timeout,
                performance_logging=True,
            )

            if analyze_fingerprinting:
                installed = install_fingerprinting_monitor(driver)
                if not installed:
                    raise RuntimeError(
                        "Failed to install fingerprinting monitor."
                    )   

            start = time.perf_counter()
            driver.get(url)
            load_seconds = time.perf_counter() - start

            # Wait until the document reports readiness. This does not
            # guarantee every third-party request has finished.
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script(
                    "return document.readyState"
                ) in ("interactive", "complete")
            )

            # Allow a consistent settling window for delayed scripts/cookies.
            time.sleep(settle_seconds)

            result = extract_measurements(
                driver,
                url,
                load_seconds,
                analyze_fingerprinting=analyze_fingerprinting,
            )

            result["Category"] = category
            result["Region"] = region
            result["Timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            result["Attempt Count"] = attempt
            result["Status"] = "Success"

            return result

        except Exception as error:
            last_error = error
            print(
                f"Attempt {attempt} failed: "
                f"{type(error).__name__}: {error}"
            )


            error_message = str(error).lower()

            verification_blocked = (
                isinstance(error, ValueError)
                and (
                    "verification page detected" in error_message
                    or "Website verification page deteted" in error_message

                )
            )

            if verification_blocked:
                print("Verification page detected. Skipping further retries.")
                


            if attempt < max_attempts and not verification_blocked:
                # Backoff: wait longer after each failure.
                retry_wait = 2 * attempt
                print(f"Retrying in {retry_wait} seconds...")
                time.sleep(retry_wait)

            
            if  (
                save_failure_screenshot
                and driver is not None
                and (verification_blocked or attempt == max_attempts)
            ):

                if screenshot_dir:
                    screenshot_path = (
                        Path(screenshot_dir)
                        / f"failed_{datetime.now():%Y%m%d_%H%M%S}.png"
                    )
                    screenshot_path.parent.mkdir(
                        parents=True, exist_ok=True
                    )
                    try:
                        driver.save_screenshot(str(screenshot_path))
                        print(f"Failure screenshot: {screenshot_path}")
                    except Exception:
                        pass
            if verification_blocked:
                    break

        finally:
            if driver is not None:
                try:
                    close_driver(driver)
                except Exception as cleanup_error:
                    print(f"Browser cleanup warning: {cleanup_error}")

    # Log one row only after all attempts have failed.
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _append_error(
        error_log_path,
        {
            "Timestamp": timestamp,
            "URL": url,
            "Category": category,
            "Region": region,
            "Attempt Count": attempt,
            "Error Type": type(last_error).__name__ if last_error else "Unknown",
            "Error Message": str(last_error).replace("\n", " ") if last_error else "",
        },
    )

    return None
