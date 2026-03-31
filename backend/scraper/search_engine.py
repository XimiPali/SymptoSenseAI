"""
scraper/search_engine.py  –  v2 (fixed)
-----------------------------------------
Reliable multi-engine web scraping using requests + BeautifulSoup.

Root-cause fixes applied
------------------------
1. requests.Session() used per engine – cookies are preserved between calls,
   making the client look like a real browser session.
2. Homepage visited before each search to pick up session cookies.
3. Expanded browser-like headers (Sec-Fetch-*, Cache-Control, Referer).
4. raise_for_status() removed – every response is logged with status code
   and HTML length so failures are visible in the console.
5. Multiple CSS-selector fallback strategies per engine (Google changed its
   HTML structure; the old /url?q= path no longer covers all results).
6. SKIP_DOMAINS tightened – no longer accidentally drops valid results.
7. DuckDuckGo POST form used as primary (more reliable than GET for HTML
   endpoint); uddg-param decoding hardened.
8. Verbose print() logging throughout for easy debugging.
"""

import time
import urllib.parse
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# ── Constants ──────────────────────────────────────────────────────────────

REQUEST_TIMEOUT:    int = 14
RESULTS_PER_ENGINE: int = 30

# Minimal set of known ad / tracking domain fragments
AD_DOMAINS: tuple = (
    "googleadservices.com",
    "googlesyndication.com",
    "doubleclick.net",
    "/aclk?",
    "bat.bing.com",
    "bing.com/aclick",
    "duckduckgo.com/y.js",
    "amazon-adsystem.com",
)

# Only skip search-engine internal pages – NOT the whole domain
SKIP_DOMAINS: tuple = (
    "accounts.google.com",
    "maps.google.com",
    "google.com/maps",
    "webcache.googleusercontent.com",
    "translate.google.com",
    "support.google.com",
    "policies.google.com",
)

# Google-owned domains to exclude from results
GOOGLE_DOMAINS: tuple = (
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "googleusercontent.com",
    "google.co.",
)

# Full browser-like headers — Sec-Fetch-* fields significantly reduce blocking
BASE_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language":          "en-US,en;q=0.9",
    "Accept-Encoding":          "gzip, deflate",   # omit 'br' – requests has no built-in brotli decoder
    "Connection":               "keep-alive",
    "Upgrade-Insecure-Requests":"1",
    "Sec-Fetch-Dest":           "document",
    "Sec-Fetch-Mode":           "navigate",
    "Sec-Fetch-Site":           "none",
    "Sec-Fetch-User":           "?1",
    "Cache-Control":            "max-age=0",
}


# ── Shared helpers ─────────────────────────────────────────────────────────

def _make_session(extra_headers: Optional[Dict] = None) -> requests.Session:
    """Return a session pre-loaded with browser-like headers."""
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    if extra_headers:
        session.headers.update(extra_headers)
    return session


def _fetch(session: requests.Session, url: str,
           method: str = "GET", data: Optional[Dict] = None) -> Optional[requests.Response]:
    """
    Fetch *url* with *session*. Logs status and HTML length to stdout.
    Returns the response even on non-200 so callers can inspect HTML.
    Returns None only on network/timeout error.
    """
    try:
        if method.upper() == "POST":
            response = session.post(url, data=data, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        else:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)

        print(f"[scraper] {method} {url[:70]}  →  status={response.status_code}  len={len(response.text):,}")

        if response.status_code not in (200, 301, 302):
            print(f"[scraper] WARNING: non-200 response from {url[:50]}")

        return response
    except requests.exceptions.Timeout:
        print(f"[scraper] TIMEOUT after {REQUEST_TIMEOUT}s: {url[:70]}")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"[scraper] REQUEST ERROR: {exc}")
        return None


def _is_ad(url: str) -> bool:
    return any(frag in url for frag in AD_DOMAINS)


def _is_skip(url: str) -> bool:
    return any(domain in url for domain in SKIP_DOMAINS)


def _is_google_domain(url: str) -> bool:
    return any(gd in url for gd in GOOGLE_DOMAINS)


def _clean_url(url: str) -> str:
    """Strip common tracking parameters and remove fragment."""
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        for key in ["utm_source", "utm_medium", "utm_campaign", "utm_term",
                    "utm_content", "ref", "source", "si", "ved", "usg",
                    "sa", "sca_esv", "sca_upv"]:
            params.pop(key, None)
        clean_query = urllib.parse.urlencode(params, doseq=True)
        return urllib.parse.urlunparse(parsed._replace(query=clean_query, fragment=""))
    except Exception:
        return url


def _add_result(results: List[Dict], seen: set, url: str, engine: str) -> bool:
    """Deduplicate and append a result. Returns True if added."""
    url = url.strip()
    if not url.startswith("http"):
        return False
    if url in seen or _is_skip(url) or _is_ad(url):
        return False
    seen.add(url)
    results.append({"url": _clean_url(url), "is_ad": False, "engine": engine})
    return True


# ── Google ─────────────────────────────────────────────────────────────────

def _parse_google(html: str) -> List[str]:
    """
    Extract result URLs from Google HTML using four fallback strategies.
    Prints counts at each stage for debugging.
    """
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    seen: set = set()

    def _add(href: str) -> None:
        if href and href not in seen and not _is_google_domain(href):
            seen.add(href)
            urls.append(href)

    # ── Strategy 1: classic /url?q= redirect links ──────────────────────
    s1_count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/url?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            actual = qs.get("q", [None])[0]
            if actual and actual.startswith("http"):
                _add(actual)
                s1_count += 1
    print(f"[google] strategy-1 (/url?q=): {s1_count} links")

    # ── Strategy 2: <h3> parent anchors with direct https:// ─────────────
    s2_count = 0
    for h3 in soup.find_all("h3"):
        parent = h3.find_parent("a", href=True)
        if parent:
            href = parent["href"]
            if href.startswith("https://") and not _is_google_domain(href):
                _add(href)
                s2_count += 1
    print(f"[google] strategy-2 (h3 parent a): {s2_count} links")

    # ── Strategy 3: common result-div selectors ───────────────────────────
    s3_count = 0
    for selector in [".g a[href]", ".yuRUbf a[href]", ".MjjYud a[href]",
                     "[data-ved] a[href]", ".tF2Cxc a[href]"]:
        for a in soup.select(selector):
            href = a.get("href", "")
            if href.startswith("https://") and not _is_google_domain(href):
                _add(href)
                s3_count += 1
    print(f"[google] strategy-3 (css selectors): {s3_count} links")

    # ── Strategy 4: broad sweep – any https:// not google-owned ──────────
    s4_count = 0
    if len(urls) < 5:
        print("[google] strategy-4 (broad sweep) triggered")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("https://") and not _is_google_domain(href):
                _add(href)
                s4_count += 1
    print(f"[google] strategy-4 (broad sweep): {s4_count} links")

    print(f"[google] total unique URLs before filtering: {len(urls)}")
    return urls


def scrape_google(term: str) -> List[Dict]:
    session = _make_session({"Referer": "https://www.google.com/"})

    # Visit homepage first to get session cookies
    print("[google] fetching homepage for cookies...")
    _fetch(session, "https://www.google.com/")
    time.sleep(0.5)

    encoded = urllib.parse.quote_plus(term)
    search_url = (
        f"https://www.google.com/search"
        f"?q={encoded}&num={RESULTS_PER_ENGINE}&hl=en&gl=us&pws=0"
    )
    session.headers.update({"Referer": "https://www.google.com/", "Sec-Fetch-Site": "same-origin"})
    response = _fetch(session, search_url)
    if response is None:
        return []

    raw_urls = _parse_google(response.text)
    results: List[Dict] = []
    seen: set = set()
    for url in raw_urls:
        if len(results) >= RESULTS_PER_ENGINE:
            break
        _add_result(results, seen, url, "google")

    print(f"[google] FINAL: {len(results)} results returned")
    return results


# ── Bing ───────────────────────────────────────────────────────────────────

def _normalise_href(href: str) -> str:
    """Convert protocol-relative //example.com → https://example.com."""
    href = href.strip()
    if href.startswith("//"):
        return "https:" + href
    return href


def _parse_bing(html: str) -> List[str]:
    """Extract organic result URLs from Bing HTML using multiple selectors."""
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    seen: set = set()

    # Print first 500 chars so we can see what Bing actually returned
    print(f"[bing] HTML preview: {html[:500]!r}")

    SKIP = ("bing.com", "microsoft.com", "msn.com", "live.com")

    def _add(href: str) -> None:
        href = _normalise_href(href)  # fix // → https://
        if href.startswith("http") and not any(s in href for s in SKIP) and href not in seen:
            seen.add(href)
            urls.append(href)

    # Primary: li.b_algo h2 a
    p1 = 0
    for li in soup.find_all("li", class_="b_algo"):
        h2 = li.find("h2")
        if h2:
            a = h2.find("a", href=True)
            if a:
                _add(a["href"])
                p1 += 1
    print(f"[bing] selector li.b_algo h2 a: {p1} links")

    # Fallback 1: any <a> inside a .b_algo block
    if len(urls) < 5:
        f1 = 0
        for li in soup.find_all("li", class_="b_algo"):
            for a in li.find_all("a", href=True):
                _add(a["href"])
                f1 += 1
        print(f"[bing] fallback-1 (.b_algo all a): {f1} links")

    # Fallback 2: #b_results h2 a
    if len(urls) < 5:
        f2 = 0
        for a in soup.select("#b_results h2 a[href]"):
            _add(a["href"])
            f2 += 1
        print(f"[bing] fallback-2 (#b_results h2 a): {f2} links")

    # Fallback 3: broad sweep – every <a href> not on Bing/MS domains
    # Handles https://, http://, AND protocol-relative // hrefs
    if len(urls) < 5:
        print("[bing] fallback-3 (broad sweep) triggered")
        f3 = 0
        for a in soup.find_all("a", href=True):
            href = _normalise_href(a["href"])
            if href.startswith("http") and not any(s in href for s in SKIP):
                _add(href)
                f3 += 1
        print(f"[bing] fallback-3 (broad sweep): {f3} links")

    print(f"[bing] total unique URLs before filtering: {len(urls)}")
    return urls


def scrape_bing(term: str) -> List[Dict]:
    session = _make_session({"Referer": "https://www.bing.com/"})

    print("[bing] fetching homepage for cookies...")
    _fetch(session, "https://www.bing.com/")
    time.sleep(0.5)

    encoded = urllib.parse.quote_plus(term)
    search_url = (
        f"https://www.bing.com/search"
        f"?q={encoded}&count={RESULTS_PER_ENGINE}&setlang=en-us&cc=US"
    )
    session.headers.update({"Referer": "https://www.bing.com/", "Sec-Fetch-Site": "same-origin"})
    response = _fetch(session, search_url)
    if response is None:
        return []

    raw_urls = _parse_bing(response.text)
    results: List[Dict] = []
    seen: set = set()
    for url in raw_urls:
        if len(results) >= RESULTS_PER_ENGINE:
            break
        _add_result(results, seen, url, "bing")

    print(f"[bing] FINAL: {len(results)} results returned")
    return results


# ── DuckDuckGo ─────────────────────────────────────────────────────────────

def _decode_ddg_url(href: str) -> Optional[str]:
    """
    Decode a DuckDuckGo redirect URL.
    Handles both formats:
      //duckduckgo.com/l/?uddg=<encoded_url>
      //duckduckgo.com/l/?uddg=<encoded_url>&rut=...
    Returns the real destination URL or None if decoding fails.
    """
    if not href.startswith("http"):
        href = "https:" + href if href.startswith("//") else "https://" + href
    try:
        parsed = urllib.parse.urlparse(href)
        # parse_qs already URL-decodes values
        qs = urllib.parse.parse_qs(parsed.query)
        uddg = qs.get("uddg", [None])[0]
        if uddg and uddg.startswith("http"):
            return uddg
        # Some DDG versions double-encode; try unquoting once more
        if uddg:
            decoded = urllib.parse.unquote(uddg)
            if decoded.startswith("http"):
                return decoded
    except Exception:
        pass
    return None


def _parse_duckduckgo(html: str) -> List[str]:
    """Extract result URLs from DuckDuckGo HTML."""
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    seen: set = set()

    # Print first 500 chars so we can see what DDG actually returned
    print(f"[duckduckgo] HTML preview: {html[:500]!r}")

    def _add(href: str) -> None:
        if href and href.startswith("http") and href not in seen:
            if "duckduckgo.com" not in href:
                seen.add(href)
                urls.append(href)

    # Primary: a.result__a — each href is a DDG redirect containing uddg=<real_url>
    p1 = 0
    for a in soup.find_all("a", class_="result__a", href=True):
        href = a["href"]
        if "duckduckgo.com" in href or href.startswith("//"):
            real = _decode_ddg_url(href)
            if real:
                _add(real)
                p1 += 1
        elif href.startswith("http"):
            _add(href)
            p1 += 1
    print(f"[duckduckgo] primary (a.result__a): {p1} links")

    # Fallback 1: any <a> inside .result blocks
    if len(urls) < 5:
        f1 = 0
        for a in soup.select(".result a[href]"):
            href = a.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            if href.startswith("http") and "duckduckgo.com" not in href:
                _add(href)
                f1 += 1
        print(f"[duckduckgo] fallback-1 (.result a): {f1} links")

    # Fallback 2: result__url span text (DDG shows the raw URL as visible text)
    if len(urls) < 5:
        f2 = 0
        for span in soup.find_all("span", class_="result__url"):
            text = "https://" + span.get_text(strip=True).lstrip("https://").lstrip("http://")
            if text.startswith("http") and "duckduckgo.com" not in text:
                _add(text)
                f2 += 1
        print(f"[duckduckgo] fallback-2 (result__url spans): {f2} links")

    print(f"[duckduckgo] total unique URLs before filtering: {len(urls)}")
    return urls


def scrape_duckduckgo(term: str) -> List[Dict]:
    encoded = urllib.parse.quote_plus(term)
    session = _make_session({
        "Referer":          "https://duckduckgo.com/",
        "Origin":           "https://duckduckgo.com",
        "Accept-Language":  "en-US,en;q=0.9",
    })

    # Primary: GET https://duckduckgo.com/html/?q= (standard HTML search page)
    print("[duckduckgo] GET https://duckduckgo.com/html/")
    response = _fetch(session, f"https://duckduckgo.com/html/?q={encoded}&kl=us-en")

    # Fallback: GET https://html.duckduckgo.com/html/?q= (dedicated HTML endpoint)
    if response is None or len(response.text) < 5000:
        print(f"[duckduckgo] primary too short ({len(response.text) if response else 0} bytes), "
              f"trying html.duckduckgo.com")
        response = _fetch(session, f"https://html.duckduckgo.com/html/?q={encoded}&kl=us-en")

    if response is None:
        return []

    raw_urls = _parse_duckduckgo(response.text)
    results: List[Dict] = []
    seen: set = set()
    for url in raw_urls:
        if len(results) >= RESULTS_PER_ENGINE:
            break
        _add_result(results, seen, url, "duckduckgo")

    print(f"[duckduckgo] FINAL: {len(results)} results returned")
    return results


# ── Public dispatcher ──────────────────────────────────────────────────────

ENGINES: Dict = {
    "google":     scrape_google,
    "bing":       scrape_bing,
    "duckduckgo": scrape_duckduckgo,
}


def search(engine: str, term: str) -> List[Dict]:
    """
    Run *engine* search for *term* and return raw result dicts.
    Each dict: {"url": str, "is_ad": bool, "engine": str}
    """
    func = ENGINES.get(engine.lower())
    if func is None:
        raise ValueError(f"Unknown engine '{engine}'. Choose from: {list(ENGINES)}")
    print(f"\n{'='*60}")
    print(f"[scraper] ENGINE={engine.upper()}  TERM='{term}'")
    print(f"{'='*60}")
    return func(term)
