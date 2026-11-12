"""Analyze Chrome performance logs for network requests."""

import json
from urllib.parse import urlparse
from domain_utils import is_same_site


def _host(url):
    return (urlparse(url).hostname or "").lower().rstrip(".")

def _normalize_document_url(url):
    #Normalize a doc URL for reponse matching
    parsed = urlparse(url)

    return (
        parsed.scheme.lower(),
        (parsed.hostname or "").lower(),
        parsed.port,
        parsed.path or "/",
        parsed.query,
    )



def analyze_network_requests(driver, page_url):
    """Read Chrome performance events and summarize HTTP(S) requests."""
    try:
        entries = driver.get_log("performance")
    except Exception as error:
        raise RecursionError(
            f"Network performance logs unavailable: {error}"
        ) from error
        

    page_host = _host(page_url)
    all_urls = []
    third_party_hosts = set()
    third_party_urls = []
    resource_types = set()
    pixels = set()
    security_headers = {}
    tls_protocols = set()

    for entry in entries:
        try:
            message = json.loads(entry["message"])["message"]
            if message.get("method") != "Network.requestWillBeSent":
                if message.get("method") == "Network.responseReceived":
                    params = message.get("params", {})
                    response = params.get("response", {})
                    request_url = response.get("url", "")

                    if(
                        params.get("type") == "Document" 
                        and _normalize_document_url(request_url)
                        == _normalize_document_url(page_url)
                    ):


                        headers = {
                            str(k).lower(): str(v)
                              for k, v in (response.get("headers") or {}).items()
                              }
                        security_headers = {
                            name: headers.get(name, "") 
                            for name in (
                            "content-security-policy", 
                            "strict-transport-security", 
                            "referrer-policy"
                            )
                        }
                        details = response.get("securityDetails") or {}
                        if details.get("protocol"):
                            tls_protocols.add(str(details["protocol"]))
                continue

            params = message.get("params", {})
            request = params.get("request", {})
            request_url = request.get("url", "")

            if not request_url.startswith(("http://", "https://")):
                continue

            all_urls.append(request_url)

            resource_type = params.get("type")
            if resource_type:
                resource_types.add(resource_type)

            path = urlparse(request_url).path.lower()
            query = urlparse(request_url).query.lower()
            if resource_type == "Image" and ("pixel" in path or "beacon" in path
                                                or "collect" in path or "gif" in path
                                                or "pixel" in query):
                pixels.add(request_url)

            request_host = _host(request_url)

            if request_host and not is_same_site(request_host, page_host):
                third_party_hosts.add(request_host)
                third_party_urls.append(request_url)

        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            # Ignore malformed or unrelated performance log entries.
            continue
    if not security_headers:
        print(
            f"WARNING: No matching document response found for {page_url}. "
            "Security headers and TLS measurements may be incomplete."
        )
    return {
        "Network Requests Count": len(all_urls),
        "Third-Party Requests Count": len(third_party_urls),
        "Third-Party Request Domains": "; ".join(sorted(third_party_hosts)),
        "Network Resource Types": "; ".join(sorted(resource_types)),
        "Potential Tracking Pixel Requests Count": len(pixels),
        "Potential Tracking Pixel URLs": "; ".join(sorted(pixels)),
        "Content-Security-Policy": security_headers.get("content-security-policy", ""),
        "Strict-Transport-Security": security_headers.get("strict-transport-security", ""),
        "Referrer-Policy": security_headers.get("referrer-policy", ""),
        "TLS Protocols": "; ".join(sorted(tls_protocols)),
        "_network_urls": sorted(all_urls),
    }
