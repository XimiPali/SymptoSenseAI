"""
scraper/frequency.py
--------------------
Fetches the content of each clean URL and counts how many times the words
of the search term appear in the page text.

Uses a ThreadPoolExecutor for parallel fetching (max 5 workers) to keep
total analysis time reasonable even for 30+ URLs.
"""

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from scraper.scraper_db import TermFrequency
from scraper.search_engine import BASE_HEADERS as HEADERS

FETCH_TIMEOUT:   int = 6    # seconds per page fetch
MAX_WORKERS:     int = 5    # parallel fetch threads
MAX_URLS:        int = 50   # cap to avoid very long runs


# ── Internal helpers ───────────────────────────────────────────────────────

def _fetch_text(url: str) -> str:
    """Fetch a URL and return its visible text content. Returns '' on error."""
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=FETCH_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # Remove script / style noise
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True).lower()
    except Exception:
        return ""


def _count_occurrences(text: str, term: str) -> int:
    """
    Count total word-level occurrences of each word in *term* within *text*.
    Uses whole-word regex matching (case-insensitive, already lowercased).
    """
    if not text:
        return 0

    words = [w for w in re.split(r"\s+", term.lower()) if len(w) > 2]
    total = 0
    for word in words:
        pattern = r"\b" + re.escape(word) + r"\b"
        total  += len(re.findall(pattern, text))
    return total


# ── Public API ─────────────────────────────────────────────────────────────

def fetch_frequency(url: str, term: str) -> int:
    """Fetch *url* and return the term frequency count for that single page."""
    text = _fetch_text(url)
    return _count_occurrences(text, term)


def analyze_urls(db: Session, urls: List[str], term: str) -> Dict[str, int]:
    """
    For each URL in *urls* (capped at MAX_URLS):
      1. Fetch page content in parallel
      2. Count term word occurrences
      3. Persist results to term_frequency table
      4. Return {url: frequency} mapping

    Existing frequency records for the same (url, term) pair are updated.
    """
    urls = urls[:MAX_URLS]
    freq_map: Dict[str, int] = {}

    # Parallel fetch
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {
            executor.submit(fetch_frequency, url, term): url
            for url in urls
        }
        for future in as_completed(future_to_url):
            url   = future_to_url[future]
            count = future.result()
            freq_map[url] = count

    # Persist to DB
    for url, count in freq_map.items():
        record = TermFrequency(url=url, term=term, frequency=count)
        db.add(record)

    db.commit()
    return freq_map
