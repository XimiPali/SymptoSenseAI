# SymptoSenseAI – Healthcare AI Assistant

SymptoSenseAI is a full-stack healthcare web application that predicts potential diseases based on symptoms entered by the user. The system is powered by an **XGBoost machine learning model** trained on a structured medical dataset from Kaggle, which maps combinations of symptoms to 41 different diseases.

## Dataset

The training data comes from the **Disease Symptom Prediction** dataset on Kaggle:

[https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset](https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset)

It includes four CSV files:

- `dataset.csv` — 4,920 rows mapping diseases to up to 17 symptoms per row (41 diseases, 132 unique symptoms)
- `Symptom-severity.csv` — severity weight (1–7) for each symptom, used as model features
- `symptom_Description.csv` — plain-English description of each disease
- `symptom_precaution.csv` — up to 4 recommended precautions per disease

## What the ML Model Does

The model takes a patient's selected symptoms (plus optional age and gender) and predicts the most likely disease along with:

- A **confidence score** (0–100%)
- The **top 5 alternative diagnoses**
- The **feature contributions** — which symptoms drove the prediction most

## Web Scraping + ETL Engine

Beyond disease prediction, the project includes a second module built as a **Data Ingestion Engine**. Users can submit a multi-word search query and the system will:

- Scrape **Google, Bing, and DuckDuckGo** simultaneously using `requests` + `BeautifulSoup`
- Run an **ETL pipeline** — extract raw URLs, remove ads and duplicates, load clean results into a dedicated MySQL database (`MY_CUSTOM_BOT`)
- **Rank results by term frequency** — each page is fetched and counted for how many times the search term appears, so the most relevant pages surface at the top
- Return a ranked list of 30+ real URLs through the React UI

---

## Project Structure

```
IntuitProject/
├── dataset/                  # CSV data files
│   ├── dataset.csv
│   ├── Symptom-severity.csv
│   ├── symptom_Description.csv
│   └── symptom_precaution.csv
│
├── database/
│   ├── schema.sql            # MySQL table definitions (healthcare_ai)
│   ├── seed.py               # Populates DB from CSV files
│   └── scraper_schema.sql    # MySQL schema for MY_CUSTOM_BOT (scraper module)
│
├── backend/                  # FastAPI Python server
│   ├── main.py               # App entry point
│   ├── database.py           # SQLAlchemy engine + session (healthcare_ai)
│   ├── models.py             # ORM models
│   ├── auth.py               # JWT + password utilities
│   ├── routes/
│   │   ├── auth.py           # /api/auth/* endpoints
│   │   ├── diseases.py       # /api/diseases + /api/symptoms
│   │   ├── predictions.py    # /api/predict + /api/predictions
│   │   └── search.py         # /api/search + /api/search/history  ← NEW
│   ├── scraper/              # Web Scraping + ETL module            ← NEW
│   │   ├── __init__.py
│   │   ├── scraper_db.py     # MY_CUSTOM_BOT engine, ORM models, get_scraper_db()
│   │   ├── search_engine.py  # Google / Bing / DuckDuckGo scrapers
│   │   ├── etl.py            # Extract → Transform → Load pipeline
│   │   ├── frequency.py      # Parallel page fetch + term-frequency counter
│   │   └── pipeline.py       # Orchestrator + multi-term automation loop
│   ├── requirements.txt
│   └── .env.example
│
├── ai/                       # Machine Learning
│   ├── ai_model.py           # Train and save the model
│   ├── predict.py            # Load model and predict
│   ├── requirements.txt
│   └── model/                # Created after training
│       ├── model.pkl
│       ├── label_encoder.pkl
│       ├── symptom_list.pkl
│       └── symptom_weights.pkl
│
└── frontend/                 # React TypeScript app
    ├── package.json
    ├── tsconfig.json
    ├── public/index.html
    └── src/
        ├── index.tsx
        ├── index.css
        ├── App.tsx
        ├── api/client.ts
        ├── contexts/AuthContext.tsx
        ├── pages/
        │   ├── Login.tsx / Auth.css
        │   ├── Register.tsx
        │   ├── Dashboard.tsx / Dashboard.css
        │   └── SearchEnginePage.tsx / SearchEnginePage.css  ← NEW
        └── components/
            ├── Navbar.tsx / Navbar.css   (updated: nav links added)
            ├── SymptomSearch.tsx / SymptomSearch.css
            └── PredictionResult.tsx / PredictionResult.css
```

---

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 18+
- MySQL 8.0+

---

### Step 1 – MySQL Databases

```sql
-- In MySQL Workbench or mysql CLI:
source database/schema.sql          -- creates healthcare_ai
source database/scraper_schema.sql  -- creates MY_CUSTOM_BOT (scraper module)
```

> **Note:** `MY_CUSTOM_BOT` is also created automatically when the backend starts
> for the first time — running `scraper_schema.sql` manually is optional.

---

### Step 2 – Backend

```bash
cd backend
cp .env.example .env
# Edit .env: set DATABASE_URL with your MySQL credentials

pip install -r requirements.txt
```

---

### Step 3 – Seed the Database

```bash
cd database
python seed.py
```

---

### Step 4 – Train the AI Model

```bash
cd ai
pip install -r requirements.txt
python ai_model.py
# Outputs accuracy and saves model to ai/model/
```

---

### Step 5 – Start the Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

---

### Step 6 – Start the Frontend

```bash
cd frontend
npm install
npm start
# Opens http://localhost:3000
```

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/auth/register | Create account | No |
| POST | /api/auth/login | Get JWT token | No |
| GET | /api/auth/me | Current user | Yes |
| GET | /api/symptoms | List all symptoms | Yes |
| GET | /api/diseases | List all diseases | Yes |
| GET | /api/diseases/{name} | Disease detail | Yes |
| POST | /api/predict | Predict disease | Yes |
| GET | /api/predictions | Prediction history | Yes |
| POST | /api/search | Scrape + ETL + rank URLs by term frequency | Yes |
| GET | /api/search/history | Last 20 search queries | Yes |

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, React Router |
| Backend | Python, FastAPI, SQLAlchemy |
| AI/ML | scikit-learn, XGBoost, pandas |
| Database | MySQL 8 (`healthcare_ai` + `MY_CUSTOM_BOT`) |
| Auth | JWT (python-jose), bcrypt |
| Web Scraping | requests, BeautifulSoup4, lxml |

---

## Web Scraping + ETL Module

### MY_CUSTOM_BOT Database Tables

| Table | Description |
| ----- | ----------- |
| `search_terms` | Each query submitted (min. 4 words) |
| `search_results` | Raw URLs per engine, including `is_ad` flag |
| `clean_results` | ETL output — ads removed, duplicates eliminated |
| `term_frequency` | Term-word occurrence count per URL |

### Scraper Pipeline (`backend/scraper/`)

1. **Extract** — `search_engine.py` scrapes Google, Bing, and DuckDuckGo using `requests` + `BeautifulSoup`
2. **Transform** — `etl.py` removes ads (googleadservices, bing aclick, etc.) and deduplicates URLs
3. **Load** — clean URLs are stored in `clean_results`
4. **Analyse** — `frequency.py` fetches each page in parallel (5 threads) and counts how many times the search-term words appear
5. **Rank** — results are returned sorted by frequency (highest first)

### Automation Loop

```python
# pipeline.py — run_pipeline_multi()
for engine in engines:          # google, bing, duckduckgo
    for term in search_terms:
        run_pipeline(db, term, engines=[engine])
```

### POST /api/search — Request Body

```json
{
  "term": "machine learning healthcare symptom prediction",
  "engines": ["google", "bing", "duckduckgo"]  // optional, defaults to all
}
```

### POST /api/search — Response

```json
{
  "term": "machine learning healthcare symptom prediction",
  "total_results": 45,
  "results": [
    { "url": "https://example.com/article", "frequency": 38, "engines": ["google", "bing"] },
    ...
  ]
}
```
