"""
routes/search.py
----------------
FastAPI router for the Web Scraping + ETL Data Ingestion Engine.

Endpoints
---------
POST /api/search
    Accept a search term (≥ 4 words), trigger scraping + ETL pipeline,
    return cleaned URLs ranked by term frequency.

GET  /api/search/history
    Return the last 20 search terms run by any user.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from auth import get_current_user
from scraper.scraper_db import get_scraper_db, SearchTerm, CleanResult, TermFrequency
from scraper.pipeline import run_pipeline
from scraper.search_engine import ENGINES

router = APIRouter(prefix="/api", tags=["search"])


# ── Pydantic schemas ───────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    term:    str
    engines: Optional[List[str]] = None  # defaults to all three if omitted

    @field_validator("term")
    @classmethod
    def term_must_be_four_words(cls, v: str) -> str:
        v = v.strip()
        words = [w for w in v.split() if w]
        if len(words) < 4:
            raise ValueError(
                "Search term must contain at least 4 words. "
                f"You provided {len(words)} word(s)."
            )
        return v

    @field_validator("engines")
    @classmethod
    def validate_engines(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        valid = set(ENGINES.keys())
        bad   = [e for e in v if e not in valid]
        if bad:
            raise ValueError(
                f"Unknown engine(s): {bad}. Valid options: {sorted(valid)}"
            )
        return v


class SearchResultItem(BaseModel):
    url:       str
    frequency: int
    engines:   List[str]

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    term:         str
    total_results: int
    results:      List[SearchResultItem]


class HistoryItem(BaseModel):
    id:         int
    term:       str
    created_at: str

    class Config:
        from_attributes = True


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/search", response_model=SearchResponse)
def run_search(
    payload:      SearchRequest,
    db:           Session = Depends(get_scraper_db),
    current_user  = Depends(get_current_user),          # JWT auth required
):
    """
    Trigger the full scraping + ETL + frequency pipeline for the given term.

    Steps performed:
      1. Validate term is at least 4 words
      2. Run search across Google, Bing, DuckDuckGo (or specified engines)
      3. Extract raw URLs → Transform (remove ads, deduplicate) → Load to DB
      4. Fetch each clean page and count term-word frequency
      5. Return results sorted by frequency (highest first)

    Note: this is a synchronous endpoint; scraping may take 15–60 seconds
    depending on network speed and the number of engines.
    """
    engines = payload.engines or list(ENGINES.keys())

    try:
        results = run_pipeline(db, payload.term, engines=engines)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Pipeline error: {str(exc)}",
        ) from exc

    return SearchResponse(
        term          = payload.term,
        total_results = len(results),
        results       = [
            SearchResultItem(
                url       = r["url"],
                frequency = r["frequency"],
                engines   = r["engines"],
            )
            for r in results
        ],
    )


@router.get("/search/history", response_model=List[HistoryItem])
def get_search_history(
    db:          Session = Depends(get_scraper_db),
    current_user = Depends(get_current_user),
    limit:       int     = 20,
):
    """Return the most recent search terms (up to *limit*)."""
    terms = (
        db.query(SearchTerm)
        .order_by(SearchTerm.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        HistoryItem(
            id         = t.id,
            term       = t.term,
            created_at = t.created_at.isoformat(),
        )
        for t in terms
    ]
