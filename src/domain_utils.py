"""Shared site classification using registrable domains."""

from urllib.parse import urlparse
import tldextract

# Use the packaged Public Suffix List snapshot consistently.
extractor = tldextract.TLDExtract(suffix_list_urls=())


def registrable_domain(hostname):
    """Return the registrable domain for a hostname."""
    hostname = str(hostname or "").lower().strip(".")
    if not hostname:
        return ""

    result = extractor(hostname)

    if result.domain and result.suffix:
        return f"{result.domain}.{result.suffix}"

    return hostname


def is_same_site(host_a, host_b):
    """Compare two hosts by registrable domain."""
    if not host_a or not host_b:
        return False

    return registrable_domain(host_a) == registrable_domain(host_b)