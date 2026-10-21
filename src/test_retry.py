import csv
from datetime import datetime
from pathlib import Path
import time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options

# Setup error logging destination
BASE_DIR = Path(__file__).resolve().parent.parent
error_log_file = BASE_DIR / "data" / "error_log.csv"
error_log_file.parent.mkdir(parents=True, exist_ok=True)

# Deliberate unreachable test url to force retry evaluation
url = "http://127.0.0.1:1"

# Configure Options for fast execution
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--blink-settings=imagesEnabled=false")

driver = webdriver.Chrome(options=chrome_options)
driver.set_page_load_timeout(5)  # Strict 5 second constraint for sandbox evaluation

try:
    with open(error_log_file, "w", newline="", encoding="utf-8") as error_f:
        error_writer = csv.writer(error_f)
        error_writer.writerow(["Timestamp", "URL", "Error Type", "Message"])

        for attempt in range(1, 4):
            try:
                print(f"Attempt {attempt} of 3")
                driver.get(url)
                
                # Check for unreachable titles or localhost fallbacks
                if "127.0.0.1" in driver.title or not driver.title:
                    raise WebDriverException("Test connection failed")
                
                print("Page Title:", driver.title)
                print("Current URL:", driver.current_url)
                break  # Success! Break out of loop if connection works

            except (TimeoutException, WebDriverException) as e:
                error_msg = str(e).replace('\n', ' ')
                error_type = type(e).__name__
                print(f"Error occurred while testing {url}: {error_type}")
                
                if attempt < 3:
                    print("Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    print("Max attempts reached. Logging final sandbox failure.")
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    error_writer.writerow([timestamp, url, error_type, error_msg])

    print(f"\ test finished! Errors recorded to: {error_log_file}")

finally:
    driver.quit()