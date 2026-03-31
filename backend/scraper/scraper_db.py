"""
scraper/scraper_db.py
---------------------
Database connection and SQLAlchemy ORM models for the MY_CUSTOM_BOT database.

Automatically derives the scraper DB URL from the main DATABASE_URL env var
(same host / credentials, different database name).
The MY_CUSTOM_BOT database is created on first import if it does not exist.
"""

import os
import re
from datetime import datetime

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey,
    Integer, String, Text, create_engine, text,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

load_dotenv()

# ── Build connection URLs ──────────────────────────────────────────────────
_MAIN_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:password@localhost:3306/healthcare_ai",
)

# Replace only the database name (last path segment before optional query string)
SCRAPER_DATABASE_URL: str = os.getenv(
    "SCRAPER_DATABASE_URL",
    re.sub(r"([^/]+)(\?.*)?$", "MY_CUSTOM_BOT", _MAIN_URL),
)

# URL without any database name – used to CREATE DATABASE
_BASE_URL: str = re.sub(r"/[^/]+(\?.*)?$", "", _MAIN_URL)


def _ensure_database() -> None:
    """Create MY_CUSTOM_BOT schema if it does not already exist."""
    init_engine = create_engine(_BASE_URL, pool_pre_ping=True)
    try:
        with init_engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE DATABASE IF NOT EXISTS MY_CUSTOM_BOT "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            conn.commit()
    finally:
        init_engine.dispose()


_ensure_database()

# ── Primary engine & session factory ──────────────────────────────────────
scraper_engine = create_engine(SCRAPER_DATABASE_URL, pool_pre_ping=True)
ScraperSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=scraper_engine
)


class ScraperBase(DeclarativeBase):
    pass


# ── ORM Models ─────────────────────────────────────────────────────────────

class SearchTerm(ScraperBase):
    """A search query submitted by a user (minimum 4 words enforced in routes)."""
    __tablename__ = "search_terms"

    id         = Column(Integer, primary_key=True, index=True)
    term       = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    search_results = relationship("SearchResult", back_populates="search_term",
                                  cascade="all, delete-orphan")
    clean_results  = relationship("CleanResult",  back_populates="search_term",
                                  cascade="all, delete-orphan")


class SearchResult(ScraperBase):
    """Raw URL returned by a search engine (may include ads)."""
    __tablename__ = "search_results"

    id            = Column(Integer, primary_key=True, index=True)
    term_id       = Column(Integer, ForeignKey("search_terms.id"), nullable=False)
    search_engine = Column(String(50),  nullable=False)  # google | bing | duckduckgo
    url           = Column(Text,        nullable=False)
    is_ad         = Column(Boolean,     default=False)
    created_at    = Column(DateTime,    default=datetime.utcnow)

    search_term = relationship("SearchTerm", back_populates="search_results")


class CleanResult(ScraperBase):
    """De-duplicated, ad-free URL after ETL processing."""
    __tablename__ = "clean_results"

    id         = Column(Integer, primary_key=True, index=True)
    term_id    = Column(Integer, ForeignKey("search_terms.id"), nullable=False)
    url        = Column(Text,    nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    search_term = relationship("SearchTerm", back_populates="clean_results")


class TermFrequency(ScraperBase):
    """How many times the search term words appear in the fetched page content."""
    __tablename__ = "term_frequency"

    id        = Column(Integer, primary_key=True, index=True)
    url       = Column(Text,        nullable=False)
    term      = Column(String(500), nullable=False)
    frequency = Column(Integer,     default=0)


# ── Create all scraper tables ──────────────────────────────────────────────
ScraperBase.metadata.create_all(bind=scraper_engine)


# ── FastAPI dependency ─────────────────────────────────────────────────────
def get_scraper_db():
    """Yield a scraper DB session and ensure it is closed."""
    db = ScraperSessionLocal()
    try:
        yield db
    finally:
        db.close()
