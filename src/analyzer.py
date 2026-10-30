from urllib.parse import urlparse


def extract_measurements(driver, url: str, load_seconds: float,
                         analyze_fingerprinting: bool = False) -> dict:
    """Collect cookie, script, and basic page measurements."""
    cookies = driver.get_cookies()
    scripts = driver.find_elements("tag name", "script")

    page_host = (urlparse(driver.current_url).hostname or "").lower()
    script_urls = []
    third_party_script_domains = set()

    for script in scripts:
        src = script.get_attribute("src")
        if not src:
            continue
        script_urls.append(src)
        host = (urlparse(src).hostname or "").lower()
        if host and page_host and host != page_host:
            # This is a simple hostname comparison, not a full registrable-domain check.
            third_party_script_domains.add(host)

    fingerprint_terms = ("canvas", "webgl", "audiocontext", "fingerprint")
    fingerprint_matches = []
    if analyze_fingerprinting:
        for src in script_urls:
            if any(term in src.lower() for term in fingerprint_terms):
                fingerprint_matches.append(src)

    cookie_count = len(cookies)
    insecure_cookies = [
        c["name"] for c in cookies
        if not c.get("secure", False)
    ]
    cookies_without_httponly = [
        c["name"] for c in cookies
        if not c.get("httpOnly", False)
    ]

    # preliminary cookie-based risk classification
    if cookie_count == 0:
        risk = "Unknown"

    elif any(c.get("sameSite", "").lower() == "none" and not c.get("secure", False)
              for c in cookies):
        risk = "Red"
    elif insecure_cookies or cookies_without_httponly:
        risk = "Orange"
    else:
        risk = "Green"

    return {
        "Website": url,
        "Final URL": driver.current_url,
        "Page Title": driver.title,
        "Category": "",
        "Load Time Seconds": round(load_seconds, 2),
        "Cookie Count": cookie_count,
        "Script Count": len(scripts),
        "Third-Party Script Domains": "; ".join(sorted(third_party_script_domains)),
        "Insecure Cookie Names": "; ".join(insecure_cookies),
        "Cookies Without HttpOnly": "; ".join(cookies_without_httponly),
        "Fingerprinting Script URL Matches": "; ".join(fingerprint_matches),
        "Risk Classification": risk,
        "_cookies": cookies,
        "_scripts": script_urls,
    }