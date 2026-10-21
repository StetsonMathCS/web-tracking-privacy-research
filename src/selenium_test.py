import csv
from pathlib import Path
import time
import pandas as pd
from selenium import webdriver

# 1. Setup file paths
BASE_DIR = Path(__file__).resolve().parent.parent
excel_file = BASE_DIR / "data" / "Website_Testing.xlsx"
csv_file = BASE_DIR / "data" / "cookies_results.csv"

# 2. Load the dataset
websites = pd.read_excel(excel_file)
websites_to_test = websites.head(6)  # Select the first 6 websites for testing

# 3. Start the selenium webdriver OUTSIDE the loops
driver = webdriver.Chrome()

# Main try block ensuring the driver closes at the absolute end
try:
    # 4. Open the CSV file once in write mode and add the header
    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(
            ["Website", "Cookie Name", "Secure", "HttpOnly", "SameSite"]
        )

        #  Loop through each website one by one
        for index, row in websites_to_test.iterrows():
            url = row["URL"]

            #  Try up to 3 times for the current website
            for attempt in range(1, 4):
                # Inner try block for the individual network request
                try:
                    print(f"\nTesting website {index + 1}/6: {url}")
                    print(f"Attempt {attempt} of 3")

                    driver.set_page_load_timeout(30)  # Set timeout
                    driver.get(url)

                    # Display website information if successful
                    print("Page Title:", driver.title)
                    print("Current URL:", driver.current_url)

                    # Collect accessible cookies
                    cookies = driver.get_cookies()
                    print(f"Number of cookies: {len(cookies)}")

                    # Save cookie attributes to the open CSV
                    for cookie in cookies:
                        writer.writerow(
                            [
                                url,
                                cookie["name"],
                                cookie.get("secure"),
                                cookie.get("httpOnly"),
                                cookie.get("sameSite"),
                            ]
                        )
                    
                    break  # Success! Break out of the retry loop to go to next site

                except Exception as e:
                    print(f"Error occurred while testing {url}: {e}")
                    if attempt < 3:
                        print("Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        print("Max attempts reached. Moving to the next website.")

    print(f"\nTesting complete! Cookie results saved to: {csv_file}")

finally:
    #browser closes cleanly at the very end
    driver.quit()