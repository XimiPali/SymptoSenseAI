/**
 * components/PredictionResult.tsx  --  v3
 * User-friendly wording; influence levels instead of raw ML percentages.
 */

import React, { useState } from 'react';
import { PredictResponse } from '../api/client';
import './PredictionResult.css';

interface Props {
  result:  PredictResponse;
  onReset: () => void;
}

function confidenceLabel(pct: number): string {
  if (pct >= 70) return 'High Confidence';
  if (pct >= 40) return 'Moderate Confidence';
  return 'Low Confidence';
}

function influenceLabel(importance: number): string {
  if (importance >= 0.5) return 'Strong influence';
  if (importance >= 0.2) return 'Moderate influence';
  return 'Minor influence';
}

function influenceClass(importance: number): string {
  if (importance >= 0.5) return 'strong';
  if (importance >= 0.2) return 'moderate';
  return 'minor';
}

/** Map internal ML feature names to readable labels */
function featureLabel(feature: string): string {
  if (feature === 'age_normalized') return 'Age';
  if (feature === 'gender_male' || feature === 'gender_female') return 'Gender';
  return feature.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function ConfidenceBar({ value }: { value: number }) {
  const pct   = Math.round(value * 100);
  const color = pct >= 70 ? 'var(--success)' : pct >= 40 ? 'var(--warning)' : 'var(--danger)';
  return (
    <div className="conf-wrapper">
      <div className="conf-bar-bg">
        <div className="conf-bar-fill" style={{ width: pct + '%', background: color }} />
      </div>
      <span className="conf-label" style={{ color }}>{confidenceLabel(pct)} ({pct}%)</span>
    </div>
  );
}

export default function PredictionResult({ result, onReset }: Props) {
  const { predicted_disease, confidence, description,
          precautions, top5, feature_contributions } = result;
  const [showContribs, setShowContribs] = useState(false);

  const titleCase = (s: string) =>
    s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const capitalize = (s: string) =>
    s ? s.charAt(0).toUpperCase() + s.slice(1) : s;

  /* Merge demographic features (age_normalized / gender_male / gender_female)
     under shared labels so users don't see raw ML feature names */
  const mergedContribs = feature_contributions
    ? feature_contributions.reduce((acc, fc) => {
        const label = featureLabel(fc.feature);
        const existing = acc.find((x) => x.label === label);
        if (existing) {
          existing.importance = Math.max(existing.importance, fc.importance);
        } else {
          acc.push({ label, importance: fc.importance });
        }
        return acc;
      }, [] as { label: string; importance: number }[])
    : [];

  return (
    <div className="pred-result card">

      {/* Header */}
      <div className="pred-header">
        <div>
          <span className="pred-label">Most Likely Condition</span>
          <h2 className="pred-disease">{titleCase(predicted_disease)}</h2>
        </div>
        <button className="btn btn-outline pred-reset" onClick={onReset}>
          &#8617; New Search
        </button>
      </div>

      {/* Confidence */}
      <div className="pred-section">
        <span className="pred-section-title">Prediction Confidence</span>
        <ConfidenceBar value={confidence} />
      </div>

      {/* Other possible conditions */}
      {top5 && top5.length > 1 && (
        <div className="pred-section">
          <span className="pred-section-title">&#128203; Other Possible Conditions</span>
          <ul className="top5-list">
            {top5.map((t, i) => (
              <li key={i} className={'top5-item' + (i === 0 ? ' top5-first' : '')}>
                <span className="top5-rank">#{i + 1}</span>
                <span className="top5-name">{titleCase(t.disease)}</span>
                <span className="top5-conf">{Math.round(t.confidence * 100)}%</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Why this condition was suggested */}
      {mergedContribs.length > 0 && (
        <div className="pred-section">
          <button
            className="contribs-toggle"
            onClick={() => setShowContribs((v) => !v)}
          >
            &#128270; {showContribs ? 'Hide Explanation' : 'Why This Condition Was Suggested'}
          </button>
          {showContribs && (
            <>
              <p className="contrib-subtitle">Symptoms Influencing This Prediction</p>
              <ul className="contrib-list">
                {mergedContribs.map((fc, i) => (
                  <li key={i} className="contrib-item">
                    <span className="contrib-name">{fc.label}</span>
                    <span className={'contrib-influence ' + influenceClass(fc.importance)}>
                      {influenceLabel(fc.importance)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}

      {/* About this condition */}
      {description && (
        <div className="pred-section">
          <span className="pred-section-title">&#8505;&#65039; About This Condition</span>
          <p className="pred-description">{description}</p>
        </div>
      )}

      {/* Care recommendations */}
      {precautions.length > 0 && (
        <div className="pred-section">
          <span className="pred-section-title">&#9888;&#65039; General Care Recommendations</span>
          <ul className="pred-precautions">
            {precautions.map((p, i) => (
              <li key={i} className="pred-precaution-item">
                <span className="pred-precaution-bullet">&#8226;</span>
                {capitalize(p)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disclaimer */}
      <div className="pred-disclaimer">
        <strong className="disclaimer-title">&#9877;&#65039; Medical Disclaimer</strong>
        <p>
          This AI tool provides informational insights based on reported symptoms.
          It is not a substitute for professional medical advice, diagnosis, or treatment.
          Always consult a qualified healthcare professional for medical concerns.
        </p>
      </div>

    </div>
  );
}
