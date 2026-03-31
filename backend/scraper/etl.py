"""
scraper/etl.py
--------------
ETL (Extract → Transform → Load) pipeline for raw search results.

Extract  : pull raw URLs from search_results table for a given term
Transform: remove ads, remove duplicates, normalise URLs
Load     : write cleaned URLs into clean_results table
"""

from typing import List, Dict
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from scraper.scraper_db import SearchResult, CleanResult
from scraper.search_engine import AD_DOMAINS


# ── Extract ────────────────────────────────────────────────────────────────

def extract(raw_results: List[Dict]) -> List[Dict]:
    """
    Given a list of raw scrape dicts (url, is_ad, engine),
    return them as-is for the transform step.
    """
    return raw_results


# ── Transform ──────────────────────────────────────────────────────────────

def _is_ad_url(url: str) -> bool:
    return any(fragment in url for fragment in AD_DOMAINS)


def _normalise(url: str) -> str:
    """Return the URL with scheme + netloc + path (no query / fragment)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def transform(raw_results: List[Dict]) -> List[Dict]:
    """
    Filter out:
      - URLs already flagged as ads (is_ad=True)
      - URLs whose domain matches known ad networks
      - Duplicate normalised URLs
    Returns a deduplicated list of clean dicts.
    """
    seen_normalised: set = set()
    cleaned: List[Dict]  = []
    dropped_ad  = 0
    dropped_dup = 0

    for item in raw_results:
        url = item.get("url", "")

        # Drop ads
        if item.get("is_ad", False) or _is_ad_url(url):
            dropped_ad += 1
            continue

        # Drop empty or non-http URLs
        if not url.startswith("http"):
            continue

        # Deduplicate by normalised URL
        norm = _normalise(url)
        if norm in seen_normalised:
            dropped_dup += 1
            continue
        seen_normalised.add(norm)

        cleaned.append(item)

    print(f"[etl] transform: {len(raw_results)} in → {len(cleaned)} clean "
          f"(dropped {dropped_ad} ads, {dropped_dup} duplicates)")
    return cleaned


# ── Load ───────────────────────────────────────────────────────────────────

def load(db: Session, term_id: int, cleaned: List[Dict]) -> List[str]:
    """
    Persist cleaned URLs into the clean_results table.
    Returns the list of stored URLs.
    """
    stored_urls: List[str] = []

    for item in cleaned:
        url = item["url"]
        record = CleanResult(term_id=term_id, url=url)
        db.add(record)
        stored_urls.append(url)

    db.commit()
    return stored_urls


# ── Combined ETL ───────────────────────────────────────────────────────────

def run_etl(db: Session, term_id: int, raw_results: List[Dict]) -> List[str]:
    """
    Full ETL pass:
      1. Extract  – accept raw_results as input
      2. Transform – remove ads and duplicates
      3. Load      – persist to DB

    Returns the final list of clean URLs.
    """
    extracted = extract(raw_results)
    cleaned   = transform(extracted)
    urls      = load(db, term_id, cleaned)
    return urls
