

from __future__ import annotations

from collections import Counter
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException



# focus on fingerprinting-related names; generic terms such as
# "audio", "browser", "hash", and "track" cause many false positives.
_FINGERPRINT_URL_TERMS = (
    "fingerprint", "fingerprinting", "fpjs", "clientjs",
    "canvasfingerprint", "canvas-fingerprint", "webglfingerprint",
    "webgl-fingerprint", "audiocontextfingerprint", "audiocontext-fingerprint",
)

# URL signatures for likely fingerprinting libraries; matches require review.
_LIBRARY_SIGNATURES = {
    "FingerprintJS": ("fingerprintjs", "fp.min.js", "fp.js"),
    "ClientJS": ("client.min.js", "clientjs"),
    "AmIUnique": ("amiunique",),
    "CreepJS": ("creepjs",),
}

_MONITOR_SCRIPT = r"""
(() => {
    if (window.__fpMonitorInstalled) return;
    Object.defineProperty(window, "__fpMonitorInstalled", {
        value: true, configurable: false
    });

    const MAX_EVENTS = 1000;
    window.__fpApiCalls = [];
    window.__fpApiCallsDropped = 0;

    const record = (apiName) => {
        try {
            if (window.__fpApiCalls.length < MAX_EVENTS) {
                window.__fpApiCalls.push({
                    api: apiName,
                    timestamp: Date.now()
                });
            } else {
                window.__fpApiCallsDropped += 1;
            }
        } catch (error) {}
    };

    const wrapMethod = (prototype, methodName, label) => {
        try {
            if (!prototype || typeof prototype[methodName] !== "function") {
                return false;
            }
            const original = prototype[methodName];
            if (original.__fpWrapped) return true;

            function monitoredMethod(...args) {
                record(label);
                return Reflect.apply(original, this, args);
            }
            Object.defineProperty(monitoredMethod, "__fpWrapped", {value: true});
            prototype[methodName] = monitoredMethod;
            return true;
        } catch (error) {
            return false;
        }
    };

    if (window.HTMLCanvasElement) {
        wrapMethod(HTMLCanvasElement.prototype, "toDataURL", "Canvas.toDataURL");
        wrapMethod(HTMLCanvasElement.prototype, "toBlob", "Canvas.toBlob");
    }
    if (window.CanvasRenderingContext2D) {
        wrapMethod(CanvasRenderingContext2D.prototype, "getImageData", "Canvas.getImageData");
        wrapMethod(CanvasRenderingContext2D.prototype, "measureText", "Canvas.measureText");
    }

    for (const [constructorName, prefix] of [
        ["WebGLRenderingContext", "WebGL"],
        ["WebGL2RenderingContext", "WebGL2"]
    ]) {
        const constructor = window[constructorName];
        if (constructor) {
            wrapMethod(constructor.prototype, "getParameter", prefix + ".getParameter");
            wrapMethod(constructor.prototype, "readPixels", prefix + ".readPixels");
        }
    }

    if (window.AudioBuffer) {
        wrapMethod(AudioBuffer.prototype, "getChannelData", "Audio.getChannelData");
    }
    if (window.AnalyserNode) {
        wrapMethod(AnalyserNode.prototype, "getFloatFrequencyData", "Audio.getFloatFrequencyData");
        wrapMethod(AnalyserNode.prototype, "getByteFrequencyData", "Audio.getByteFrequencyData");
    }
})();
"""


def install_fingerprinting_monitor(driver: WebDriver) -> bool:
    """Register monitoring for future documents; call BEFORE driver.get(url).

    Requires a Chromium-based Selenium driver supporting CDP. The script is
    installed for the lifetime of this driver session, including later pages.
    """
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": _MONITOR_SCRIPT},
        )
        return True
    except (WebDriverException, AttributeError) as error:
        print(f"Fingerprint monitor installation warning: {error}")
        return False


def _get_api_availability(driver: WebDriver) -> dict[str, Any]:
    """Check API presence; presence alone does not imply fingerprinting."""
    script = """
        return {
            canvas: typeof window.HTMLCanvasElement !== "undefined",
            canvas2d: typeof window.CanvasRenderingContext2D !== "undefined",
            webgl: typeof window.WebGLRenderingContext !== "undefined",
            webgl2: typeof window.WebGL2RenderingContext !== "undefined",
            audioContext: (
                typeof window.AudioContext !== "undefined" ||
                typeof window.webkitAudioContext !== "undefined"
            )
        };
    """
    try:
        return driver.execute_script(script) or {}
    except WebDriverException:
        return {}


def _collect_storage_indicators(driver: WebDriver) -> dict[str, Any]:
    """Report Web Storage keys only; do not collect potentially sensitive values."""
    try:
        return driver.execute_script("""
            const snapshot = storage => {
                try { return Array.from({length: storage.length}, (_, i) => storage.key(i)).filter(Boolean); }
                catch (e) { return []; }
            };
            return {local: snapshot(window.localStorage), session: snapshot(window.sessionStorage)};
        """) or {}
    except WebDriverException:
        return {"local": [], "session": []}


def _match_library_urls(script_urls: list[str]) -> list[str]:
    urls = [str(url).lower() for url in script_urls or []]
    return sorted(name for name, terms in _LIBRARY_SIGNATURES.items()
                  if any(term in url for term in terms for url in urls))


def _get_recorded_api_calls(driver: WebDriver) -> list[dict[str, Any]]:
    """Read recorded calls from the current top-level document."""
    try:
        calls = driver.execute_script("return window.__fpApiCalls || [];")
        return calls if isinstance(calls, list) else []
    except WebDriverException:
        return []


def _get_dropped_call_count(driver: WebDriver) -> int:
    try:
        count = driver.execute_script("return window.__fpApiCallsDropped || 0;")
        return int(count) if isinstance(count, (int, float)) else 0
    except WebDriverException:
        return 0


def _get_script_urls(driver: WebDriver) -> list[str]:
    """Collect script src attributes from the current document."""
    try:
        urls = driver.execute_script(
            "return Array.from(document.scripts, s => s.src).filter(Boolean);"
        )
        return [str(url) for url in urls] if isinstance(urls, list) else []
    except WebDriverException:
        return []


def _match_script_urls(script_urls: list[str] | None) -> list[str]:
    """Find script URLs with fingerprint-related terms (not definitive proof)."""
    matches = []
    for script_url in script_urls or []:
        url = str(script_url).strip()
        if url and any(term in url.lower() for term in _FINGERPRINT_URL_TERMS):
            matches.append(url)
    return sorted(set(matches))


def collect_fingerprinting_indicators(
    driver: WebDriver, script_urls: list[str] | None = None
) -> dict[str, Any]:
    """Collect indicators after navigation"""

    # verify the monitor is active before collecting data
    if not _monitor_active(driver):
        raise RuntimeError(
            "Fingerprinting monitor is inactive on this page. "
            
        )
    api_calls = _get_recorded_api_calls(driver)

    if not _monitor_active(driver):
        raise RuntimeError(
            "Fingerprinting monitor is inactive on this page. "
            "Measurements may be incomplete."
        )

    api_availability = _get_api_availability(driver)
    urls = _get_script_urls(driver) if script_urls is None else script_urls
    url_matches = _match_script_urls(urls)
    library_matches = _match_library_urls(urls)
    storage = _collect_storage_indicators(driver)

    api_names = sorted({
        str(item.get("api", "Unknown"))
        for item in api_calls if isinstance(item, dict)
    })
    api_counts = Counter(
        str(item.get("api", "Unknown"))
        for item in api_calls if isinstance(item, dict)
    )
    dropped = _get_dropped_call_count(driver)
    indicator_detected = bool(api_calls or url_matches or library_matches)

    return {
        "Fingerprinting API Calls Count": len(api_calls),
        "Fingerprinting API Names": "; ".join(api_names),
        "Fingerprinting Script URL Matches": "; ".join(url_matches),
        "Potential Fingerprinting Libraries": "; ".join(library_matches),
        "LocalStorage Key Count": len(storage.get("local", [])),
        "LocalStorage Keys": "; ".join(sorted(storage.get("local", []))),
        "SessionStorage Key Count": len(storage.get("session", [])),
        "SessionStorage Keys": "; ".join(sorted(storage.get("session", []))),
        "Fingerprinting Indicators Detected": indicator_detected,
        "Canvas API Available": api_availability.get("canvas", ""),
        "Canvas 2D API Available": api_availability.get("canvas2d", ""),
        "WebGL API Available": api_availability.get("webgl", ""),
        "WebGL2 API Available": api_availability.get("webgl2", ""),
        "AudioContext API Available": api_availability.get("audioContext", ""),
        "Fingerprinting Evidence Level": (
            "Observed API use or URL indicator"
            if api_calls
            else "Script URL or library signature indicator only"
            if url_matches or library_matches
            else "No monitored indicator observed"
        
        ),
        "Canvas API Calls Count": sum(v for k, v in api_counts.items() if k.startswith("Canvas.")),
        "WebGL API Calls Count": sum(v for k, v in api_counts.items() if k.startswith(("WebGL.", "WebGL2."))),
        "Audio API Calls Count": sum(v for k, v in api_counts.items() if k.startswith("Audio.")),
        "Fingerprinting API Calls Dropped": dropped,
        "Fingerprinting Monitor Active": _monitor_active(driver),
    }


def _monitor_active(driver: WebDriver) -> bool:
    """Distinguish an installed monitor from a page with no observed calls."""
    try:
        return driver.execute_script("return window.__fpMonitorInstalled === true;") is True
    except WebDriverException:
        return False
