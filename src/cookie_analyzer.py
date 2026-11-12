"""Cookie attribute extraction and preliminary risk indicators."""

from domain_utils import is_same_site



def analyze_cookies(cookies, page_scheme, page_host=""):
    """
    Analyze cookies returned by Selenium.

    Important:
    - Missing HttpOnly is not automatically a vulnerability. Some cookies
      need to be readable by JavaScript.
    - This is a preliminary indicator, not a full security audit.
    - A cookie's Secure flag and SameSite behavior should be interpreted
      in the context of the site's intended functionality.
    """
    insecure_names = []
    no_httponly_names = []
    no_samesite_names = []
    samesite_none_names = []
    secure_names = []
    httponly_names = []
    samesite_set_names = []
    third_party_names = []
    first_party_count = 0
    third_party_count = 0

    for cookie in cookies:
        name = cookie.get("name", "Unknown")
        cookie_domain = str(cookie.get("domain") or page_host).lower().lstrip(".")
        page_domain = str(page_host or "").lower().lstrip(".")
        is_first_party = is_same_site(cookie_domain, page_domain)

        if is_first_party:
            first_party_count += 1
        else:
            third_party_count += 1

        if not cookie.get("secure", False):
            insecure_names.append(name)
        else:
            secure_names.append(name)

        if not cookie.get("httpOnly", False):
            no_httponly_names.append(name)
        else:
            httponly_names.append(name)

        same_site = str(cookie.get("sameSite") or "").strip().lower()

        if not same_site:
            no_samesite_names.append(name)
        else:
            samesite_set_names.append(name)

        if same_site == "none":
            samesite_none_names.append(name)

        # Selenium exposes a cookie's domain, but not always enough context
        # to establish whether it is genuinely third-party. This field is
        # therefore left to request-level analysis rather than guessed here.

    if not cookies:
        risk = "No Cookies Observed"
    elif page_scheme.lower() == "http":
        risk = "Not Assessed"
    elif any(
        str(c.get("sameSite") or "").lower() == "none"
        and not c.get("secure", False)
        for c in cookies
    ):
        risk = "Red"
    elif any(not c.get("secure", False) for c in cookies):
        risk = "Orange"
    else:
        risk = "Green"

    return {
        "Cookies Count": len(cookies),
        "First-Party Cookies Count": first_party_count,
        "Third-Party Cookies Count": third_party_count,
        "Secure Cookie Names": "; ".join(sorted(set(secure_names))),
        "HttpOnly Cookie Names": "; ".join(sorted(set(httponly_names))),
        "SameSite Cookie Names": "; ".join(sorted(set(samesite_set_names))),
        "Insecure Cookie Names": "; ".join(sorted(set(insecure_names))),
        "Cookies Without HttpOnly": "; ".join(sorted(set(no_httponly_names))),
        "Cookies Without SameSite": "; ".join(sorted(set(no_samesite_names))),
        "SameSite None Cookies": "; ".join(sorted(set(samesite_none_names))),
        "Risk Classification": risk,
    }
