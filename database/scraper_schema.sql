-- =============================================================================
-- scraper_schema.sql
-- Database: MY_CUSTOM_BOT
-- Purpose : Stores raw search results, cleaned URLs, and term-frequency data
--           for the Advanced Web Scraping + ETL Data Ingestion Engine module.
-- Run     : mysql -u root -p < database/scraper_schema.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS MY_CUSTOM_BOT
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE MY_CUSTOM_BOT;

-- ---------------------------------------------------------------------------
-- 1. search_terms
--    Stores each unique search query submitted by users.
--    Constraint: term must be at least 4 words (enforced in application layer).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_terms (
    id         INT          NOT NULL AUTO_INCREMENT,
    term       VARCHAR(500) NOT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_term (term(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 2. search_results  (raw / unfiltered)
--    Every URL returned by a search engine for a given term, including ads.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS search_results (
    id            INT          NOT NULL AUTO_INCREMENT,
    term_id       INT          NOT NULL,
    search_engine VARCHAR(50)  NOT NULL COMMENT 'google | bing | duckduckgo',
    url           TEXT         NOT NULL,
    is_ad         BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_sr_term_id      (term_id),
    INDEX idx_sr_search_engine (search_engine),
    CONSTRAINT fk_sr_term FOREIGN KEY (term_id)
        REFERENCES search_terms (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. clean_results  (post-ETL)
--    De-duplicated, ad-free URLs ready for frequency analysis.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clean_results (
    id         INT      NOT NULL AUTO_INCREMENT,
    term_id    INT      NOT NULL,
    url        TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_cr_term_id (term_id),
    CONSTRAINT fk_cr_term FOREIGN KEY (term_id)
        REFERENCES search_terms (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 4. term_frequency
--    How many times each search term appears in the content of a URL.
--    Higher frequency = more relevant result.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS term_frequency (
    id        INT          NOT NULL AUTO_INCREMENT,
    url       TEXT         NOT NULL,
    term      VARCHAR(500) NOT NULL,
    frequency INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    INDEX idx_tf_term (term(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
