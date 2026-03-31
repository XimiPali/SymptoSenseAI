/**
 * api/client.ts  --  v2
 * Changes: RegisterPayload + UserResponse now carry gender + age.
 * SymptomInput is { name, duration }. PredictResponse adds top5 + feature_contributions.
 */

import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = 'Bearer ' + token;
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

// ---------- Typed interfaces ----------

export interface LoginPayload    { username: string; password: string }
export interface RegisterPayload {
  username: string;
  email:    string;
  password: string;
  gender:   'male' | 'female';
  age:      number;
}
export interface TokenResponse { access_token: string; token_type: string }
export interface UserResponse  { id: number; username: string; email: string; gender: string; age: number }

export interface SymptomItem    { id: number; name: string; weight: number }
export interface DiseaseItem    { id: number; name: string; description: string | null }
export interface PrecautionItem { precaution_order: number; precaution_text: string }
export interface DiseaseDetail extends DiseaseItem {
  precautions: PrecautionItem[];
  symptoms:    string[];
}

/** One selected symptom with its reported duration in days. */
export interface SymptomInput  { name: string; duration: number }

export interface PredictRequest {
  symptoms: SymptomInput[];
  age?:     number;
  gender?:  string;
}

export interface Top5Item            { disease: string; confidence: number }
export interface FeatureContribution { feature: string; value: number; importance: number }

export interface PredictResponse {
  predicted_disease:     string;
  confidence:            number;
  description:           string;
  precautions:           string[];
  top5:                  Top5Item[];
  feature_contributions: FeatureContribution[];
}

export interface PredictionHistory {
  id:               number;
  symptoms_input:   Array<string | SymptomInput>;
  predicted_disease: string;
  confidence:       number;
  age_at_prediction:    number | null;
  gender_at_prediction: string | null;
  created_at:       string;
}

// ---------- API helpers ----------

export const authAPI = {
  login: (data: LoginPayload) =>
    apiClient.post<TokenResponse>('/api/auth/login',
      new URLSearchParams({ username: data.username, password: data.password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  register: (data: RegisterPayload) =>
    apiClient.post<UserResponse>('/api/auth/register', data),
  me: () =>
    apiClient.get<UserResponse>('/api/auth/me'),
};

export const diseasesAPI = {
  listSymptoms: () => apiClient.get<SymptomItem[]>('/api/symptoms'),
  listDiseases: () => apiClient.get<DiseaseItem[]>('/api/diseases'),
  getDisease:   (name: string) =>
    apiClient.get<DiseaseDetail>('/api/diseases/' + encodeURIComponent(name)),
};

export const predictionsAPI = {
  predict: (data: PredictRequest) =>
    apiClient.post<PredictResponse>('/api/predict', data),
  history: () =>
    apiClient.get<PredictionHistory[]>('/api/predictions'),
};

// ── Search Engine / ETL module ─────────────────────────────────────────────

export interface SearchRequest {
  term:     string;
  engines?: string[];
}

export interface SearchResultItem {
  url:       string;
  frequency: number;
  engines:   string[];
}

export interface SearchApiResponse {
  term:          string;
  total_results: number;
  results:       SearchResultItem[];
}

export interface HistoryItem {
  id:         number;
  term:       string;
  created_at: string;
}

export const searchAPI = {
  search:  (data: SearchRequest) =>
    apiClient.post<SearchApiResponse>('/api/search', data),
  history: () =>
    apiClient.get<HistoryItem[]>('/api/search/history'),
};
