"""Main controller for the website privacy measurement project."""

from pathlib import Path
import sys
import pandas as pd
from retry_handler import run_website_with_retries

project_dir = Path(__file__).resolve().parent.parent


data_dir = project_dir / "data"
screenshot_dir = data_dir / "screenshots"
excel_path = data_dir / "Website_Testing.xlsx"
results_path = data_dir / "FinalRun2_test_results.csv"
error_log_path = data_dir / "FinalRun2_test_errors.csv"
error_screenshot_dir = screenshot_dir / "FinalRun2_test_screenshots"
sheet_name = "Website Testing"


# None processes every valid website in the input spreadsheet.
max_websites = None

#test modes fresh , resume , retry
RUN_MODE = "fresh"

RETRY_ERROR_TYPES = {
    "TimeoutException","WebDriveException",
}


MAX_ATTEMPTS = 3
HEADLESS = False
PAGE_LOAD_TIMEOUT = 45
SETTLE_SECONDS = 6
ANALYZE_FINGERPRINTING = True
SAVE_FAILURE_SCREENSHOTS = False

REQUIRED_COLUMNS = ["URL", "Category", "Region"]
RESULT_COLUMNS = [
    "Website", "Final URL", "Page Title", "Category", "Region", "Status",
    "Measurement Quality", "Attempt Count", "Timestamp", "Load Time Seconds",
    "Cookies Count", "Scripts Count", "Overall Risk Classification",
    "Risk Factors", "First-Party Cookies Count", 
    "Third-Party Cookies Count", "Secure Cookie Names", 
    "HttpOnly Cookie Names", "SameSite Cookie Names",
    "External Scripts Count", "Inline Scripts Count",
    "Third-Party Script Domains", "Insecure Cookie Names",
    "Cookies Without HttpOnly", "Cookies Without SameSite",
    "SameSite None Cookies", "Risk Classification",
    "Network Requests Count", "Third-Party Requests Count",
    "Third-Party Request Domains", "Network Resource Types",
    "Fingerprinting API Calls Count", "Fingerprinting API Names",
    "Fingerprinting Indicators Detected",
    "Fingerprinting Evidence Level",
    "Canvas API Calls Count", "WebGL API Calls Count", 
    "Audio API Calls Count",
    "Canvas API Available", "Canvas 2D API Available",
    "WebGL API Available", "WebGL2 API Available",
    "AudioContext API Available",
    "Fingerprinting API Calls Dropped",
    "Fingerprinting Monitor Active",
    "Fingerprinting Script URL Matches",
    "Potential Fingerprinting Libraries",
    "LocalStorage Key Count", "LocalStorage Keys",
    "SessionStorage Key Count", "SessionStorage Keys",
    "Potential Tracking Pixel Requests Count", "Potential Tracking Pixel URLs",
    "Content-Security-Policy", "Strict-Transport-Security", "Referrer-Policy",
    "TLS Protocols",
    "Cross-Domain Redirect",
    "Original Domain",
    "Final Domain",
]


def normalize_url(url):
    """Normalize URL text for consistent matching between CSVs and Excel."""
    if pd.isna(url):
        return ""
    return str(url).strip().lower()


def append_results(new_results, output_path):
    """Append result rows while preserving older columns."""
    if not new_results:
        return

    new_df = pd.DataFrame(new_results)
    new_df = new_df.drop(
        columns=["_cookies", "_scripts", "_network_urls"], errors="ignore"
    )
    for column in RESULT_COLUMNS:
        if column not in new_df.columns:
            new_df[column] = ""
    new_df = new_df[RESULT_COLUMNS]

    if output_path.exists() and output_path.stat().st_size > 0:
        old_df = pd.read_csv(output_path)
        combined = pd.concat([old_df, new_df], ignore_index=True, sort=False)
    else:
        combined = new_df

    combined.to_csv(output_path, index=False, encoding="utf-8")


def get_completed_websites(results_path):
    """Return normalized URLs marked Success in the saved summary CSV."""
    if not results_path.exists() or results_path.stat().st_size == 0:
        return set()
    previous = pd.read_csv(results_path)
    if not {"Website", "Status"}.issubset(previous.columns):
        return set()
    successful = previous.loc[
        previous["Status"].astype(str).str.strip().str.lower() == "success",
        "Website",
    ].dropna()
    return {normalized for value in successful if (normalized := normalize_url(value))}


def get_failed_websites(log_path):
    """Return normalized URLs whose final failures were logged."""
    if not log_path.exists() or log_path.stat().st_size == 0:
        return set()
    previous = pd.read_csv(log_path)
    if "URL" not in previous.columns:
        return set()
    return {
        normalized
        for value in previous["URL"].dropna()
        if (normalized := normalize_url(value))
    }


def main():
    """Load the sample, test eligible websites, and save the final summary."""
    data_dir.mkdir(parents=True, exist_ok=True)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    error_screenshot_dir.mkdir(parents=True, exist_ok=True)



    if RUN_MODE == "fresh":
        if results_path.exists() and results_path.stat().st_size > 0:
            raise FileExistsError(
                f"Results file already exists: {results_path}"
            )
        if error_log_path.exists() and error_log_path.stat().st_size > 0:
            raise FileExistsError(
                f"Fresh run requested, but error log file already exists: {error_log_path}"
            )

    if not excel_path.exists():
        raise FileNotFoundError(f"Dataset not found: {excel_path}")

    websites = pd.read_excel(excel_path, sheet_name=sheet_name)
    missing = [column for column in REQUIRED_COLUMNS if column not in websites.columns]
    if missing:
        raise ValueError(f"Excel file is missing required columns: {missing}")

    websites = websites.dropna(subset=["URL"]).copy()
    websites["URL"] = websites["URL"].astype(str).str.strip()
    websites = websites[websites["URL"] != ""]

    #check for duplicate website URLd before testing
    normalized_urls = websites["URL"].apply(normalize_url)

    duplicates = websites.loc[
        normalized_urls.duplicated(keep=False)
        
    ]

    if not duplicates.empty:
        print("\nWARNING: Duplicate website URLs detected:")
        print(duplicates[["URL", "Category", "Region"]])

        raise ValueError(
            f"Dataset contains {len(duplicates)} rows with duplicate URLs."
            "Please correct the Execel file before testing"


        )





    print("\nDATASET SUMMARY")
    print("-" * 55)
    print(f"Valid websites: {len(websites)}")
    print("Category counts:")
    print(websites["Category"].value_counts(dropna=False))
    print("\nRegion counts:")
    print(websites["Region"].value_counts(dropna=False))
    if len(websites) == 120:
        region_counts = websites["Region"].astype(str).str.strip().str.lower().value_counts()
        us_count = sum(region_counts.get(label, 0) for label in ("us", "u.s.", "usa", "united states", "united states of america"))
        international_count = sum(region_counts.get(label, 0) for label in ("international", "intl", "non-us", "non-us/international"))
        if us_count and international_count and (us_count, international_count) != (88, 32):
            print(f"WARNING: Expected 88 U.S./32 international sites; found {us_count}/{international_count}.")
    if websites["Category"].nunique(dropna=True) != 4:
        print(f"WARNING: Expected 4 categories, found {websites['Category'].nunique(dropna=True)}.")
    if len(websites) != 120:
        print(f"\nWARNING: Expected 120 websites, found {len(websites)}.")

# Select websites based on the testing mode (fresh, resume, retry)
    if RUN_MODE == "fresh":
        completed_websites = set()
        failed_websites = set()
        skipped_websites = set()
    elif RUN_MODE == "resume":
        completed_websites = get_completed_websites(results_path)
        failed_websites = get_failed_websites(error_log_path)
        skipped_websites = completed_websites.union(failed_websites)

    elif RUN_MODE == "retry":
        completed_websites = get_completed_websites(results_path)
        failed_websites = get_failed_websites(error_log_path)

        if error_log_path.exists() and error_log_path.stat().st_size > 0:
            errors_df = pd.read_csv(error_log_path)
        else:
            errors_df = pd.DataFrame(
                columns=["URL", "Error Type"]
            )

        retry_urls = set(
            errors_df.loc[
                errors_df["Error Type"].isin(RETRY_ERROR_TYPES),
                "URL"
            ].dropna().apply(normalize_url)
        )

        skipped_websites = (
            set(websites["URL"].apply(normalize_url))
            - retry_urls
        ).union(completed_websites)

        print(f"Selected {len(retry_urls)} websites for retry.")

    else:
        raise ValueError(f"Invalid RUN_MODE: {RUN_MODE}")



    remaining_websites = websites.loc[
        ~websites["URL"].apply(normalize_url).isin(skipped_websites)
    ].copy()

    print("\n" + "=" * 50)
    print("WEBSITE SKIPPING SUMMARY")
    print("=" * 50)
    print(f"Previously completed websites: {len(completed_websites)}")
    print(f"Previously failed websites: {len(failed_websites)}")
    print(f"Total unique skipped URLs: {len(skipped_websites)}")
    print(f"Websites remaining to test: {len(remaining_websites)}")
    print("=" * 50)

    if max_websites is not None:
        test_websites = remaining_websites.head(max_websites)
    else:
        test_websites = remaining_websites

    success_count = 0
    failure_count = 0

    for position, (_, row) in enumerate(test_websites.iterrows(), start=1):
        url = row["URL"]
        category = row["Category"]
        region = row["Region"]

        print("\n" + "=" * 70)
        print(f"WEBSITE {position}/{len(test_websites)}: {url}")
        print(f"Category: {category} | Region: {region}")
        print("=" * 70)

        result = run_website_with_retries(
            url=url,
            category=category,
            region=region,
            error_log_path=error_log_path,
            max_attempts=MAX_ATTEMPTS,
            headless=HEADLESS,
            page_load_timeout=PAGE_LOAD_TIMEOUT,
            settle_seconds=SETTLE_SECONDS,
            analyze_fingerprinting=ANALYZE_FINGERPRINTING,
            save_failure_screenshot=SAVE_FAILURE_SCREENSHOTS,
            screenshot_dir=error_screenshot_dir,
        )

        if result is not None:
            success_count += 1
            print("\nMeasurement summary:")
            print("Cookies:", result.get("Cookies Count"))
            print("Scripts:", result.get("Scripts Count"))
            print("Third-party requests:", result.get("Third-Party Requests Count"))
            print("Cookie risk:", result.get("Risk Classification"))
            print("Overall risk:", result.get("Overall Risk Classification"))
            print("Fingerprinting detected:", result.get("Fingerprinting Indicators Detected"))





            # Save after each successful website, not only at the end of the batch.
            append_results([result], results_path)
        else:
            failure_count += 1
            print(f"\nWebsite failed after {MAX_ATTEMPTS} attempts.")

    print("\n" + "=" * 70)
    print("FINAL TESTING SUMMARY")
    print("=" * 70)
    print(f"Websites selected: {len(test_websites)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failure_count}")
    print(f"Results: {results_path}")
    print(f"Errors: {error_log_path}")
    print("\nTesting completed.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTesting interrupted by user.")
        sys.exit(130)
