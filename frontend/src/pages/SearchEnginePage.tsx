/**
 * pages/SearchEnginePage.tsx
 * --------------------------
 * Mini search-engine UI for the Web Scraping + ETL Data Ingestion Engine module.
 *
 * Features
 * --------
 * - Search term input (minimum 4 words enforced)
 * - Engine selector: All / Google / Bing / DuckDuckGo
 * - "Run Search" button triggers POST /api/search
 * - Results table sorted by term frequency (≥ 30 results)
 * - Recent search history sidebar
 * - Loading skeleton + error handling
 */

import React, { useState, useEffect, useRef } from 'react';
import Navbar from '../components/Navbar';
import { searchAPI, SearchResultItem, HistoryItem } from '../api/client';
import './SearchEnginePage.css';

const ENGINE_OPTIONS = [
  { value: 'all',        label: '🌐 All Engines' },
  { value: 'google',     label: '🔍 Google' },
  { value: 'bing',       label: '🅱 Bing' },
  { value: 'duckduckgo', label: '🦆 DuckDuckGo' },
];

const ENGINE_BADGE: Record<string, string> = {
  google:     'badge-google',
  bing:       'badge-bing',
  duckduckgo: 'badge-ddg',
};

function wordCount(s: string): number {
  return s.trim().split(/\s+/).filter(Boolean).length;
}

function truncateUrl(url: string, max = 60): string {
  return url.length > max ? url.slice(0, max) + '…' : url;
}

function getDomain(url: string): string {
  try { return new URL(url).hostname.replace('www.', ''); }
  catch { return url; }
}

export default function SearchEnginePage() {
  const [term,        setTerm]        = useState('');
  const [engine,      setEngine]      = useState('all');
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState('');
  const [termError,   setTermError]   = useState('');
  const [results,     setResults]     = useState<SearchResultItem[] | null>(null);
  const [resultTerm,  setResultTerm]  = useState('');
  const [history,     setHistory]     = useState<HistoryItem[]>([]);
  const [visibleCount, setVisibleCount] = useState(30);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load recent search history on mount
  useEffect(() => {
    searchAPI.history()
      .then(res => setHistory(res.data))
      .catch(() => {});
  }, []);

  const validate = (): boolean => {
    if (wordCount(term) < 4) {
      setTermError('Please enter at least 4 words.');
      inputRef.current?.focus();
      return false;
    }
    setTermError('');
    return true;
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setError('');
    setResults(null);
    setVisibleCount(30);

    const engines = engine === 'all' ? undefined : [engine];

    try {
      const res = await searchAPI.search({ term: term.trim(), engines });
      setResults(res.data.results);
      setResultTerm(res.data.term);
      // Refresh history
      searchAPI.history().then(r => setHistory(r.data)).catch(() => {});
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        'Search failed. Make sure the backend is running and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleHistoryClick = (t: string) => {
    setTerm(t);
    setTermError('');
  };

  const visibleResults = results?.slice(0, visibleCount) ?? [];

  return (
    <div className="se-page">
      <Navbar />

      <div className="se-body">
        {/* ── Main column ── */}
        <main className="se-main">

          {/* Hero search box */}
          <div className="se-hero card">
            <div className="se-hero-title">
              <span className="se-hero-icon">🔎</span>
              <span>Web Search &amp; ETL Engine</span>
            </div>
            <p className="se-hero-sub">
              Enter a search query (min. 4 words) to scrape Google, Bing &amp; DuckDuckGo,
              clean the results and rank them by how often your terms appear on each page.
            </p>

            <form className="se-form" onSubmit={handleSearch} noValidate>
              <div className="se-input-row">
                <input
                  ref={inputRef}
                  className={`form-input se-input${termError ? ' se-input--error' : ''}`}
                  type="text"
                  placeholder="e.g. machine learning healthcare symptom prediction"
                  value={term}
                  onChange={e => { setTerm(e.target.value); setTermError(''); }}
                  disabled={loading}
                  autoComplete="off"
                />
                <select
                  className="se-engine-select"
                  value={engine}
                  onChange={e => setEngine(e.target.value)}
                  disabled={loading}
                >
                  {ENGINE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
                <button
                  type="submit"
                  className="btn btn-primary se-btn"
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <span className="se-spinner" />
                      Searching…
                    </>
                  ) : (
                    <>🚀 Run Search</>
                  )}
                </button>
              </div>

              {termError && <p className="error-text se-term-error">{termError}</p>}
              <p className="se-hint">Tip: the more specific your query, the better the results.</p>
            </form>
          </div>

          {/* Error */}
          {error && (
            <div className="se-error card">
              <span>❌</span> {error}
            </div>
          )}

          {/* Loading skeleton */}
          {loading && (
            <div className="se-loading card">
              <div className="se-loading-inner">
                <span className="se-spinner se-spinner--lg" />
                <div>
                  <p className="se-loading-title">Running pipeline…</p>
                  <p className="se-loading-sub">
                    Scraping engines → cleaning results → analysing page content.
                    This may take 20–60 seconds.
                  </p>
                </div>
              </div>
              {[1,2,3,4,5].map(i => (
                <div key={i} className="se-skeleton-row">
                  <div className="se-skeleton se-skeleton--url" />
                  <div className="se-skeleton se-skeleton--freq" />
                </div>
              ))}
            </div>
          )}

          {/* Results */}
          {results !== null && !loading && (
            <div className="se-results card">
              <div className="se-results-header">
                <span className="se-results-title">
                  📋 {results.length} result{results.length !== 1 ? 's' : ''} for&nbsp;
                  <em>"{resultTerm}"</em>
                </span>
                <span className="se-results-sorted">sorted by frequency ↓</span>
              </div>

              {results.length === 0 ? (
                <p className="se-no-results">
                  No results found. The search engines may be blocking automated
                  requests. Try again or use a different query.
                </p>
              ) : (
                <>
                  <table className="se-table">
                    <thead>
                      <tr>
                        <th className="se-th se-th-rank">#</th>
                        <th className="se-th se-th-url">URL</th>
                        <th className="se-th se-th-domain">Domain</th>
                        <th className="se-th se-th-engines">Engines</th>
                        <th className="se-th se-th-freq">Frequency</th>
                      </tr>
                    </thead>
                    <tbody>
                      {visibleResults.map((r, idx) => (
                        <tr key={idx} className="se-tr">
                          <td className="se-td se-td-rank">{idx + 1}</td>
                          <td className="se-td se-td-url">
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="se-link"
                              title={r.url}
                            >
                              {truncateUrl(r.url)}
                            </a>
                          </td>
                          <td className="se-td se-td-domain">
                            <span className="tag">{getDomain(r.url)}</span>
                          </td>
                          <td className="se-td se-td-engines">
                            {r.engines.map(eng => (
                              <span
                                key={eng}
                                className={`se-engine-badge ${ENGINE_BADGE[eng] ?? ''}`}
                              >
                                {eng}
                              </span>
                            ))}
                          </td>
                          <td className="se-td se-td-freq">
                            <span className={`se-freq-bar-wrap`}>
                              <span
                                className="se-freq-bar"
                                style={{
                                  width: `${Math.min(
                                    100,
                                    results[0]?.frequency
                                      ? (r.frequency / results[0].frequency) * 100
                                      : 0
                                  )}%`,
                                }}
                              />
                              <span className="se-freq-num">{r.frequency}</span>
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {results.length > visibleCount && (
                    <button
                      className="btn btn-outline se-load-more"
                      onClick={() => setVisibleCount(c => c + 30)}
                    >
                      Show more ({results.length - visibleCount} remaining)
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </main>

        {/* ── History sidebar ── */}
        <aside className="se-sidebar">
          <div className="se-history card">
            <h3 className="se-history-title">🕐 Recent Searches</h3>
            {history.length === 0 ? (
              <p className="se-history-empty">No searches yet.</p>
            ) : (
              <ul className="se-history-list">
                {history.map(h => (
                  <li key={h.id} className="se-history-item">
                    <button
                      className="se-history-btn"
                      onClick={() => handleHistoryClick(h.term)}
                      title="Click to re-run this search"
                    >
                      <span className="se-history-term">{h.term}</span>
                      <span className="se-history-date">
                        {new Date(h.created_at).toLocaleDateString()}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Engine legend */}
          <div className="se-legend card">
            <h4 className="se-legend-title">Engines Used</h4>
            <div className="se-legend-row">
              <span className="se-engine-badge badge-google">google</span>
              <span className="se-legend-desc">google.com/search</span>
            </div>
            <div className="se-legend-row">
              <span className="se-engine-badge badge-bing">bing</span>
              <span className="se-legend-desc">bing.com/search</span>
            </div>
            <div className="se-legend-row">
              <span className="se-engine-badge badge-ddg">duckduckgo</span>
              <span className="se-legend-desc">html.duckduckgo.com</span>
            </div>
            <p className="se-legend-note">
              Ads and duplicates are removed automatically by the ETL pipeline.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
