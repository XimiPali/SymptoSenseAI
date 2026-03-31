/**
 * components/SymptomSearch.tsx  --  v2
 * Each selected symptom now tracks a duration (days, default 1).
 * onPredict receives SymptomInput[] instead of string[].
 */

import React, { useState, useEffect, useRef } from 'react';
import { diseasesAPI, SymptomItem, SymptomInput } from '../api/client';
import './SymptomSearch.css';

interface Props {
  onPredict: (symptoms: SymptomInput[]) => void;
  loading:   boolean;
}

export default function SymptomSearch({ onPredict, loading }: Props) {
  const [allSymptoms, setAllSymptoms] = useState<SymptomItem[]>([]);
  const [selected,    setSelected]    = useState<SymptomInput[]>([]);
  const [query,       setQuery]       = useState('');
  const [open,        setOpen]        = useState(false);
  const [fetchError,  setFetchError]  = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    diseasesAPI.listSymptoms()
      .then((res) => setAllSymptoms(res.data))
      .catch(() => setFetchError('Could not load symptoms. Is the backend running?'));
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node))
        setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectedNames = selected.map((s) => s.name);

  const filtered = query
    ? allSymptoms.filter((s) => s.name.toLowerCase().includes(query.toLowerCase()))
    : allSymptoms;

  const toggle = (name: string) => {
    setSelected((prev) =>
      prev.some((s) => s.name === name)
        ? prev.filter((s) => s.name !== name)
        : [...prev, { name, duration: 1 }]
    );
  };

  const setDuration = (name: string, val: number) => {
    setSelected((prev) =>
      prev.map((s) => s.name === name ? { ...s, duration: Math.max(1, val) } : s)
    );
  };

  const remove = (name: string) =>
    setSelected((prev) => prev.filter((s) => s.name !== name));

  const displayName = (n: string) =>
    n.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="symptom-search card">
      <h2 className="symptom-search-title">&#128269; Search Symptoms</h2>
      <p className="symptom-search-sub">
        Select symptoms and enter how many <strong>days</strong> you have had each one.
      </p>

      {fetchError && <p className="error-text">{fetchError}</p>}

      {selected.length > 0 && (
        <div className="selected-symptoms-list">
          {selected.map((s) => (
            <div key={s.name} className="selected-symptom-row">
              <span className="selected-symptom-name">{displayName(s.name)}</span>
              <div className="duration-control">
                <label className="duration-label">Days:</label>
                <input
                  type="number" min={1} max={365}
                  className="duration-input"
                  aria-label={'Duration in days for ' + displayName(s.name)}
                  value={s.duration}
                  onChange={(e) => setDuration(s.name, Number(e.target.value))}
                />
              </div>
              <button type="button" className="remove-tag" onClick={() => remove(s.name)} title="Remove">
                &#x2715;
              </button>
            </div>
          ))}
          <button type="button" className="clear-all" onClick={() => setSelected([])}>Clear all</button>
        </div>
      )}

      <div className="symptom-dropdown-wrapper" ref={containerRef}>
        <input
          className="form-input symptom-input"
          placeholder="Type to search symptoms..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
        />
        {open && filtered.length > 0 && (
          <ul className="symptom-dropdown">
            {filtered.slice(0, 80).map((s) => (
              <li
                key={s.id}
                className={'symptom-option' + (selectedNames.includes(s.name) ? ' selected' : '')}
                onMouseDown={(e) => { e.preventDefault(); toggle(s.name); }}
              >
                <span className="symptom-check">{selectedNames.includes(s.name) ? '\u2713' : ''}</span>
                {displayName(s.name)}
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        type="button"
        className="btn btn-primary predict-btn"
        onClick={() => { if (selected.length > 0) onPredict(selected); }}
        disabled={selected.length === 0 || loading}
      >
        {loading ? '\u23F3 Predicting\u2026' : '\uD83E\uDDEC Predict Disease'}
      </button>

      {selected.length === 0 && (
        <p className="symptom-hint">Select at least one symptom to enable prediction.</p>
      )}
    </div>
  );
}
