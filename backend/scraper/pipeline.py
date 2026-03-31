"""
scraper/pipeline.py
-------------------
Orchestrates the full scraping + ETL + frequency-analysis pipeline.

Flow
----
For each (engine, term) pair:
  1. Scrape  – call search_engine.search(engine, term)
  2. Store   – persist raw results to search_results table
  3. ETL     – extract / transform / load into clean_results
  4. Analyse – fetch pages, count term frequency, store in term_frequency

Final output: list of result dicts sorted by frequency (descending).

Automation loop example
-----------------------
    for engine in engines:
        for term in search_terms:
            run_pipeline(db, term, engines=[engine])
"""

from typing import Dict, List

from sqlalchemy.orm import Session

from scraper.scraper_db import SearchResult, SearchTerm
from scraper.search_engine import ENGINES, search
from scraper.etl import run_etl
from scraper.frequency import analyze_urls


# ── Internal helpers ───────────────────────────────────────────────────────

def _get_or_create_term(db: Session, term: str) -> SearchTerm:
    """Return an existing SearchTerm row or create a new one."""
    existing = (
        db.query(SearchTerm)
        .filter(SearchTerm.term == term)
        .order_by(SearchTerm.id.desc())
        .first()
    )
    if existing:
        return existing

    record = SearchTerm(term=term)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _store_raw_results(
    db: Session,
    term_id: int,
    raw_results: List[Dict],
) -> None:
    """Bulk-insert raw scrape results into search_results table."""
    for item in raw_results:
        db.add(
            SearchResult(
                term_id       = term_id,
                search_engine = item["engine"],
                url           = item["url"],
                is_ad         = item.get("is_ad", False),
            )
        )
    db.commit()


# ── Public pipeline ────────────────────────────────────────────────────────

def run_pipeline(
    db:      Session,
    term:    str,
    engines: List[str] | None = None,
) -> List[Dict]:
    """
    Execute the full scrape → ETL → frequency pipeline for *term*.

    Parameters
    ----------
    db      : SQLAlchemy session for MY_CUSTOM_BOT
    term    : search query (must be ≥ 4 words – enforced in the route layer)
    engines : list of engine names to use; defaults to all three

    Returns
    -------
    Sorted list of dicts:
        [{"url": str, "frequency": int, "engines": [str, ...]}, ...]
    """
    if engines is None:
        engines = list(ENGINES.keys())   # google, bing, duckduckgo

    # 1. Persist / retrieve search term
    term_record = _get_or_create_term(db, term)
    term_id     = term_record.id

    all_raw:   List[Dict] = []
    all_clean: List[str]  = []

    # 2 + 3. Scrape each engine and run ETL
    for engine in engines:
        try:
            raw = search(engine, term)
        except Exception as exc:
            print(f"[pipeline] ERROR scraping {engine}: {exc}")
            raw = []

        print(f"[pipeline] {engine}: {len(raw)} raw results")
        if raw:
            _store_raw_results(db, term_id, raw)
            clean_urls = run_etl(db, term_id, raw)
            print(f"[pipeline] {engine}: {len(clean_urls)} clean URLs after ETL")
            all_clean.extend(clean_urls)
            all_raw.extend(raw)
        else:
            print(f"[pipeline] {engine}: scraper returned 0 results — check logs above")

    # Deduplicate clean URLs across engines
    seen: set = set()
    deduped_clean: List[str] = []
    for url in all_clean:
        if url not in seen:
            seen.add(url)
            deduped_clean.append(url)

    # 4. Frequency analysis
    freq_map: Dict[str, int] = {}
    if deduped_clean:
        freq_map = analyze_urls(db, deduped_clean, term)

    # Build engine-source mapping for each URL
    url_to_engines: Dict[str, List[str]] = {}
    for item in all_raw:
        if not item.get("is_ad", False):
            url_to_engines.setdefault(item["url"], [])
            if item["engine"] not in url_to_engines[item["url"]]:
                url_to_engines[item["url"]].append(item["engine"])

    # 5. Assemble and sort results by frequency (descending)
    results: List[Dict] = []
    for url in deduped_clean:
        results.append(
            {
                "url":       url,
                "frequency": freq_map.get(url, 0),
                "engines":   url_to_engines.get(url, []),
            }
        )

    results.sort(key=lambda r: r["frequency"], reverse=True)
    print(f"[pipeline] DONE — {len(results)} total results for '{term}'")
    return results


def run_pipeline_multi(
    db:           Session,
    terms:        List[str],
    engines:      List[str] | None = None,
) -> Dict[str, List[Dict]]:
    """
    Automation loop: run the full pipeline for multiple terms across all engines.

    Example (mirrors the professor's requested loop):
        for engine in engines:
            for term in search_terms:
                run_pipeline(engine, term)

    Returns a mapping of term → sorted results.
    """
    if engines is None:
        engines = list(ENGINES.keys())

    all_results: Dict[str, List[Dict]] = {}

    for engine in engines:
        for term in terms:
            results = run_pipeline(db, term, engines=[engine])
            if term not in all_results:
                all_results[term] = results
            else:
                # Merge and re-sort results from different engines
                existing_urls = {r["url"] for r in all_results[term]}
                for r in results:
                    if r["url"] not in existing_urls:
                        all_results[term].append(r)
                all_results[term].sort(key=lambda r: r["frequency"], reverse=True)

    return all_results
