"""Coordinate cookie, script, network, and optional fingerprinting analysis."""

from urllib.parse import urlparse

from cookie_analyzer import analyze_cookies
from fingerprint_analyzer import collect_fingerprinting_indicators
from network_analyzer import analyze_network_requests
from domain_utils import is_same_site



def extract_measurements(
    driver,
    url: str,
    load_seconds: float,
    analyze_fingerprinting: bool = True,
) -> dict:
    """Collect a single website's measurements after navigation."""
    final_url = driver.current_url
    page_title = driver.title

    original_domain = (urlparse (url).hostname or "").lower()
    final_damain = (urlparse(final_url).hostname or "").lower()

    def normalize_domain(domain):
        return domain.removeprefix("www.")
        
    cross_domain_redirect = (
        normalize_domain(original_domain)
        != normalize_domain(final_damain)
    )

    if cross_domain_redirect:
        print(f"WARNING: Cross-domain redirected: {url} -> {final_url}")


    blocked_title = [
        "just a moment...",
        "privacy error",
        "your connection is not private",
        "access denied",
        "attention required",
        "verify you are human",
        "captcha",
        
    ]

    if any(text in page_title.lower() for text in blocked_title):
        raise ValueError(f"Website verification page detected: {page_title}"
        )

    html_length = len(driver.page_source)

    print(f"Final URL: {final_url}")
    print(f"Page Title: {page_title}")
    print("HTML Length:", html_length)

    if html_length < 500:
        raise ValueError(
            f"Suspiciously short HTML length response:"
            f" {html_length} characters for {final_url}"
        )

    #detect common anti-bot or verification pages
    page_html = driver.page_source.lower()

    blocking_indicators = [
        "ct.captcha-delivery.com",
        "checking your browser",
        "enable javascript and cookies",
        "datadone captcha",
        "verify you are human",
    ]

    matched_indicators = [

        indicator
        for indicator in blocking_indicators
        if indicator in page_html

    ]

    if matched_indicators:
        print(f"Verification indicators found: {matched_indicators}")

        if html_length < 5000:
            raise ValueError(
                f"Possible verification page detected for {final_url}. "
                f"Indocators: {matched_indicators}"
                
            )    

    # Read cookie data using Selenium's native cookie interface.
    cookies = driver.get_cookies()

    # Read script elements in one JavaScript operation to reduce stale
    # element problems on pages that dynamically modify their DOM.
    script_data = driver.execute_script("""
        return Array.from(document.scripts).map(script => ({
            src: script.src || "",
            inline: script.src ? "" : (script.textContent || "")
        }));
    """) or []

    script_urls = [
        item.get("src", "")
        for item in script_data
        if item.get("src")
    ]

    inline_script_count = sum(
        1 for item in script_data
        if not item.get("src") and item.get("inline", "").strip()
    )

    page_host = (urlparse(final_url).hostname or "").lower()
    third_party_script_domains = set()

    for script_url in script_urls:
        script_host = (
            urlparse(script_url).hostname or ""
        ).lower()


        if script_host and not is_same_site(script_host, page_host):
            third_party_script_domains.add(script_host)

    cookie_results = analyze_cookies(
        cookies,
        urlparse(final_url).scheme,
        page_host=(urlparse(final_url).hostname or "").lower(),
    )

    network_results = analyze_network_requests(
        driver,
        final_url,
    )

 # Collect fingerprinting indicators
    if analyze_fingerprinting:
        fingerprint_results = collect_fingerprinting_indicators(
            driver,
            script_urls=script_urls,
        )
    else:
        fingerprint_results = {}

        # Preliminary combined privacy and security assessment

    cookie_risk = cookie_results.get("Risk Classification", "Unknown")

    fingerprint_detected = fingerprint_results.get(
    "Fingerprinting Indicators Detected", False
)

    overall_risk = "Unknown"

    if cookie_risk == "No Cookies Observed":
        overall_risk = "Orange" if fingerprint_detected else "No Cookies Observed"
    elif cookie_risk == "Red":
        overall_risk = "Red"
    elif cookie_risk == "Orange":
        overall_risk = "Orange"
    elif cookie_risk == "Green" and fingerprint_detected:
        overall_risk = "Orange"
    elif cookie_risk == "Green":
        overall_risk = "Green"

# Assess measurement completeness, not website security risk.
    quality_issues = []

    network_count = network_results.get(
        "Network Requests Count", 0
    )

    tls_protocols = network_results.get(
        "TLS Protocols", ""
    )

    if not tls_protocols:
        quality_issues.append("TLS information not captured")

    if network_count <= 5:
        quality_issues.append("Unusually low network request count")

    if analyze_fingerprinting and not fingerprint_results.get(
        "Fingerprinting Monitor Active", False
    ):
        quality_issues.append("Fingerprinting monitor inactive")

    if quality_issues:
        measurement_quality = "Incomplete"
    else:
        measurement_quality = "Valid"

    


    result = {
        "Website": url,
        "Final URL": final_url,
        "Page Title": page_title,
        "Category": "",
        "Region": "",
        "Timestamp": "",
        "Overall Risk Classification": overall_risk,
        "Risk Factors": "; ".join(filter(None, [
            "Insecure cookie attributes" if cookie_risk in ("Red", "Orange") else "",
            "Fingerprinting indicator observed" if fingerprint_detected else "",
        ])),
        "Cross-Domain Redirect": cross_domain_redirect,
        "Original Domain": original_domain,
        "Final Domain": final_damain,
        "Load Time Seconds": round(load_seconds, 2),
        "Scripts Count": len(script_data),
        "External Scripts Count": len(script_urls),
        "Inline Scripts Count": inline_script_count,
        "Third-Party Script Domains": "; ".join(
            sorted(third_party_script_domains)
        ),
        **cookie_results,
        **network_results,
        **fingerprint_results,
        "Status": "Success",
        "Measurement Quality": measurement_quality,
        # Keep internal structures private; main.py removes them before CSV.
        "_cookies": cookies,
        "_scripts": script_urls,
    }

    return result
