from pathlib import Path
import pandas as pd
from analyzer import extract_measurements
from browser import create_driver
import time
import sys

#Locate the project directory
project_dir = Path(__file__).resolve().parent.parent

#Locate the Excel file dateset
excel_path = project_dir / "data" / "Website_Testing.xlsx"

#Read the Excel file
websites = pd.read_excel(
    excel_path,
    sheet_name = "Website Testing"
)

#preview the dateset
print(websites.head())

print("Column names:")
print(websites.columns.tolist())

#count the websites 
print("Total websites to test:", len(websites))

#preview the first three websites
for index, row in websites.head(3).iterrows():
    url = row["URL"]
    category = row["Category"]
    region = row["Region"]
    print(f"URL: {url}, Category: {category}, Region: {region}")
# Test only the first 3 websites
test_websites = websites.head(3)
results = []

for index, row in test_websites.iterrows():
    url = row["URL"]
    driver = None

    print(f"\nTesting: {url}")

    for attempt in range(1, 4):
        try:
            driver = create_driver()
            driver.set_page_load_timeout(30)

            start = time.perf_counter()
            driver.get(url)
            load_seconds = time.perf_counter() - start

            time.sleep(2)

            result = extract_measurements(
                driver,
                url,
                load_seconds,
                analyze_fingerprinting=True
            )

            result["Category"] = row["Category"]
            result["Region"] = row["Region"]
            result["Status"] = "Success"

            # Keep CSV fields, not internal Python lists
            result.pop("_cookies", None)
            result.pop("_scripts", None)

            results.append(result)

            print("Risk:", result["Risk Classification"])
            break

        except Exception as error:
            print(f"Attempt {attempt} failed: {error}")

            if attempt == 3:
                results.append({
                    "Website": url,
                    "Category": row["Category"],
                    "Region": row["Region"],
                    "Status": "Failed",
                    "Error": str(error)
                })

            else:
                time.sleep(5)

        finally:
            if driver is not None:
                driver.quit()
                driver = None

# Save results separately from cookie-level data
output_file = project_dir / "data" / "website_results.csv"

pd.DataFrame(results).to_csv(
    output_file,
    index=False,
    encoding="utf-8"
)

print(f"\nResults saved to: {output_file}")