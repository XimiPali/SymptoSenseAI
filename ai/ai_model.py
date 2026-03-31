"""
ai_model.py  --  v2
-------------------
Trains an XGBoost classifier on dataset.csv and saves all model artifacts.

Improvements over v1:
  * XGBoost (XGBClassifier) instead of Random Forest
  * Symptom features: weight * log(1 + duration)
    (duration sampled synthetically 1-14 days during training)
  * Demographic features: age_normalized, gender_male, gender_female (synthetic)
  * 5-fold Stratified Cross-Validation before final fit
  * Feature importance: top-20 printed + saved to feature_importance.csv
  * Final model trained on the FULL dataset after CV

Usage:
    cd ai
    pip install -r requirements.txt
    python ai_model.py

Artifacts -> ai/model/:
    model.pkl               XGBClassifier
    label_encoder.pkl       LabelEncoder for disease names
    symptom_list.pkl        ordered symptom feature names
    symptom_weights.pkl     {symptom: severity_weight}
    feature_names.pkl       all feature names including demographics
    feature_importances.pkl np.ndarray parallel to feature_names
    feature_importance.csv  human-readable table
"""

import warnings
warnings.filterwarnings('ignore')

import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

# -- Paths -----------------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR.parent / 'dataset'
MODEL_DIR   = BASE_DIR / 'model'
MODEL_DIR.mkdir(exist_ok=True)

DATASET_PATH  = DATASET_DIR / 'dataset.csv'
SEVERITY_PATH = DATASET_DIR / 'Symptom-severity.csv'

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)


# -- 1. Load & clean -------------------------------------------------------

def load_dataset() -> pd.DataFrame:
    df = pd.read_csv(DATASET_PATH)
    df.columns = df.columns.str.strip()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    df.replace('nan', np.nan, inplace=True)
    return df


def load_severity() -> dict:
    df = pd.read_csv(SEVERITY_PATH)
    df.columns = df.columns.str.strip()
    df['Symptom'] = df['Symptom'].astype(str).str.strip()
    return dict(zip(df['Symptom'], df['weight'].astype(float)))


# -- 2. Build feature matrix -----------------------------------------------
#
# Feature layout:
#   [ symptom_0...symptom_N | age_normalized | gender_male | gender_female ]
#
# Symptom value = severity_weight * log(1 + duration)
#   Training : duration ~ Uniform[1, 14] (synthetic)
#   Inference: actual patient-reported duration
#
# Demographics are synthetic during training; real values used at inference.

def build_features(df: pd.DataFrame, symptom_weights: dict):
    symptom_cols = [c for c in df.columns if c.startswith('Symptom_')]

    all_symptoms: set = set()
    for col in symptom_cols:
        all_symptoms.update(df[col].dropna().unique())
    all_symptoms.discard('nan')
    symptom_list  = sorted(all_symptoms)
    symptom_index = {s: i for i, s in enumerate(symptom_list)}

    n = len(df)
    X_symptoms = np.zeros((n, len(symptom_list)), dtype=np.float32)

    for row_idx, row in df.iterrows():
        for col in symptom_cols:
            symptom = row[col]
            if pd.notna(symptom) and symptom in symptom_index:
                col_idx  = symptom_index[symptom]
                weight   = float(symptom_weights.get(symptom, 1))
                duration = np.random.randint(1, 15)
                X_symptoms[row_idx, col_idx] = weight * np.log1p(duration)

    ages = np.clip(np.random.normal(40, 18, n).astype(int), 0, 120)
    age_norm      = (ages / 120.0).astype(np.float32).reshape(-1, 1)
    gender_male   = np.random.randint(0, 2, n).astype(np.float32)
    gender_female = (1 - gender_male).astype(np.float32)
    X_demo = np.column_stack([age_norm, gender_male, gender_female])

    X             = np.hstack([X_symptoms, X_demo])
    feature_names = symptom_list + ['age_normalized', 'gender_male', 'gender_female']
    y             = df['Disease'].values
    return X, y, symptom_list, feature_names


# -- 3. XGBoost hyperparameters --------------------------------------------

def make_clf() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='mlogloss',
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


# -- 4. Training pipeline --------------------------------------------------

def train():
    print('=' * 62)
    print('Healthcare AI  --  XGBoost Training Pipeline  (v2)')
    print('=' * 62)

    print('\n[1/5] Loading dataset ...')
    df = load_dataset()
    n_diseases = df['Disease'].nunique()
    print(f'      Rows: {len(df)}  |  Unique diseases: {n_diseases}')

    print('\n[2/5] Loading symptom severity weights ...')
    symptom_weights = load_severity()
    print(f'      Symptoms with known severity: {len(symptom_weights)}')

    print('\n[3/5] Building feature matrix ...')
    X, y_raw, symptom_list, feature_names = build_features(df, symptom_weights)
    n_sym = len(symptom_list)
    print(f'      Symptom features  : {n_sym}')
    print( '      Demographic feats : 3  (age_normalized, gender_male, gender_female)')
    print(f'      Total features    : {X.shape[1]}')
    print(f'      Total samples     : {X.shape[0]}')

    le = LabelEncoder()
    y  = le.fit_transform(y_raw)
    print(f'      Classes (diseases): {len(le.classes_)}')

    print('\n[4/5] 5-fold Stratified Cross-Validation ...')
    print('      (Each fold trains XGBoost 300 trees -- ~2-5 min total)')
    skf       = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(make_clf(), X, y, cv=skf, scoring='accuracy', n_jobs=1)
    fold_str  = str([str(round(s, 4)) for s in cv_scores])
    print(f'      Fold accuracies : {fold_str}')
    print(f'      Mean accuracy   : {cv_scores.mean():.4f}  ({cv_scores.mean()*100:.2f}%)')
    print(f'      Std deviation   : {cv_scores.std():.4f}')

    print('\n[5/5] Training final XGBoost on full dataset ...')
    clf = make_clf()
    clf.fit(X, y)
    train_acc = accuracy_score(y, clf.predict(X))
    print(f'      Training accuracy (full data): {train_acc:.4f}')

    importances = clf.feature_importances_
    feat_df = (
        pd.DataFrame({'feature': feature_names, 'importance': importances})
        .sort_values('importance', ascending=False)
        .reset_index(drop=True)
    )

    print('\n-- Top 20 Most Important Features --------------------------------')
    print(feat_df.head(20).to_string(index=False))
    print('-' * 62)

    fi_path = MODEL_DIR / 'feature_importance.csv'
    feat_df.to_csv(fi_path, index=False)
    print(f'\nFeature importance table saved -> {fi_path}')

    joblib.dump(clf,             MODEL_DIR / 'model.pkl')
    joblib.dump(le,              MODEL_DIR / 'label_encoder.pkl')
    joblib.dump(symptom_list,    MODEL_DIR / 'symptom_list.pkl')
    joblib.dump(symptom_weights, MODEL_DIR / 'symptom_weights.pkl')
    joblib.dump(feature_names,   MODEL_DIR / 'feature_names.pkl')
    joblib.dump(importances,     MODEL_DIR / 'feature_importances.pkl')

    print(f'\nAll model artifacts saved to: {MODEL_DIR}')
    print('\nDone\!')


if __name__ == '__main__':
    train()
