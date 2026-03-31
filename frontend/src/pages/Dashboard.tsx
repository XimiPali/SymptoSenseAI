/**
 * pages/Dashboard.tsx  --  v2
 * handlePredict receives SymptomInput[] and passes user demographics.
 * History shows gender_at_prediction badge.
 */

import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import SymptomSearch from '../components/SymptomSearch';
import PredictionResult from '../components/PredictionResult';
import { predictionsAPI, PredictResponse, PredictionHistory, SymptomInput } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import './Dashboard.css';

export default function Dashboard() {
  const { user } = useAuth();
  const [result,       setResult]       = useState<PredictResponse | null>(null);
  const [predicting,   setPredicting]   = useState(false);
  const [predictError, setPredictError] = useState('');
  const [history,      setHistory]      = useState<PredictionHistory[]>([]);

  const loadHistory = () => {
    predictionsAPI.history()
      .then((res) => setHistory(res.data))
      .catch(() => { /* silently ignore */ });
  };

  useEffect(() => { loadHistory(); }, []);

  const handlePredict = async (symptoms: SymptomInput[]) => {
    setPredicting(true);
    setPredictError('');
    setResult(null);
    try {
      const res = await predictionsAPI.predict({
        symptoms,
        age:    user?.age,
        gender: user?.gender,
      });
      setResult(res.data);
      loadHistory();
    } catch (err: any) {
      setPredictError(
        err.response?.data?.detail || 'Prediction failed. Please check the backend.'
      );
    } finally {
      setPredicting(false);
    }
  };

  const displayName = (n: string) =>
    n.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  const historyLabels = (item: PredictionHistory): string[] =>
    item.symptoms_input.map((s) =>
      typeof s === 'string' ? displayName(s) : displayName((s as SymptomInput).name)
    );

  return (
    <div className="dashboard">
      <Navbar />
      <div className="dashboard-body">

        <main className="dashboard-main">
          <div className="welcome-banner card">
            <h2>&#128075; Welcome{user ? ', ' + user.username : ''}</h2>
            <p>
              Select your symptoms, set duration in days, and our AI predicts
              the most likely disease with precautions and recommendations.
            </p>
            {user && (
              <p style={{ marginTop: '0.35rem', fontSize: '0.85rem', color: 'var(--gray-500)' }}>
                Profile: {user.age} yrs &bull; {user.gender}
              </p>
            )}
          </div>

          <SymptomSearch onPredict={handlePredict} loading={predicting} />

          {predictError && (
            <div className="predict-error card">
              <p className="error-text">&#10060; {predictError}</p>
            </div>
          )}

          {result && (
            <PredictionResult result={result} onReset={() => setResult(null)} />
          )}
        </main>

        <aside className="dashboard-history">
          <div className="history-card card">
            <h3 className="history-title">&#128203; Prediction History</h3>
            {history.length === 0 ? (
              <p className="history-empty">No predictions yet. Try searching for symptoms!</p>
            ) : (
              <ul className="history-list">
                {history.map((item) => {
                  const labels = historyLabels(item);
                  return (
                    <li key={item.id} className="history-item">
                      <div className="history-disease">{item.predicted_disease}</div>
                      <div className="history-meta">
                        <span className="badge badge-blue">
                          {Math.round(item.confidence * 100)}%
                        </span>
                        <span className="history-date">
                          {new Date(item.created_at).toLocaleDateString()}
                        </span>
                        {item.gender_at_prediction && (
                          <span className="tag">{item.gender_at_prediction}</span>
                        )}
                      </div>
                      <div className="history-symptoms">
                        {labels.slice(0, 3).map((s, i) => (
                          <span key={i} className="tag">{s}</span>
                        ))}
                        {labels.length > 3 && (
                          <span className="tag">+{labels.length - 3} more</span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>

      </div>
    </div>
  );
}
