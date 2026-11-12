import csv
from pathlib import Path


from retry_handler import run_website_with_retries

result = run_website_with_retries(
    url="https://example.com",
    category="Test",
    region="Test",
    error_log_path="data/integration_error_log.csv",
    max_attempts=1,
    analyze_fingerprinting=True,
)
if result:
    print("\n=== INTEGRATION TEST RESULTS ===")

    for key, value in result.items():
        if not key.startswith("_"):
            print(f"{key}: {value}")

    # Save results to a separate CSV
    output_path = Path("data/fingerprinting_test_results.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_result = {
        key: value
        for key, value in result.items()
        if not key.startswith("_")
    }

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=csv_result.keys())
        writer.writeheader()
        writer.writerow(csv_result)

    print(f"\nResults saved to: {output_path}")

else:
    print("Integration test did not return results.")