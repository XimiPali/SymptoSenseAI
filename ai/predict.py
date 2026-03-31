"""
predict.py  --  v2
------------------
Loads trained XGBoost artifacts and exposes:

    predict_disease(symptoms, age=None, gender=None) -> dict

Parameters
----------
symptoms : list of str  OR  list of dict {name: str, duration: int}
    Symptom names (spaces or underscores both accepted).
    When dicts are passed, the duration (days) is used to scale the feature.
    Backward-compatible: plain strings default to duration = 1.
age    : int or None   Patient age (0-120). Uses stored user age if omitted.
gender : str or None   'male' or 'female'. Uses stored user gender if omitted.

Returns
-------
dict:
    disease              str
    confidence           float  0.0-1.0
    top5                 list of {disease, confidence}
    feature_contributions list of {feature, value, importance}  (top-5 drivers)
"""

import joblib
import numpy as np
from pathlib import Path
from typing import Optional, List, Union

MODEL_DIR = Path(__file__).resolve().parent / 'model'

# Lazy-loaded singletons
_model               = None
_label_encoder       = None
_symptom_list        = None
_symptom_weights     = None
_feature_names       = None
_feature_importances = None


def _load_artifacts():
    global _model, _label_encoder, _symptom_list
    global _symptom_weights, _feature_names, _feature_importances

    if _model is not None:
        return

    required = [
        'model.pkl', 'label_encoder.pkl', 'symptom_list.pkl',
        'symptom_weights.pkl', 'feature_names.pkl', 'feature_importances.pkl',
    ]
    for name in required:
        path = MODEL_DIR / name
        if not path.exists():
            raise FileNotFoundError(
                f'Model artifact not found: {path}\n'
                'Run  python ai/ai_model.py  first to train the model.'
            )

    _model               = joblib.load(MODEL_DIR / 'model.pkl')
    _label_encoder       = joblib.load(MODEL_DIR / 'label_encoder.pkl')
    _symptom_list        = joblib.load(MODEL_DIR / 'symptom_list.pkl')
    _symptom_weights     = joblib.load(MODEL_DIR / 'symptom_weights.pkl')
    _feature_names       = joblib.load(MODEL_DIR / 'feature_names.pkl')
    _feature_importances = joblib.load(MODEL_DIR / 'feature_importances.pkl')


def _normalise_name(raw: str) -> str:
    return raw.strip().lower().replace(' ', '_')


def _build_vector(
    symptoms: list,
    age: Optional[int],
    gender: Optional[str],
) -> np.ndarray:
    _load_artifacts()

    n_symptoms  = len(_symptom_list)
    total_feats = len(_feature_names)          # symptoms + 3 demographic
    vec          = np.zeros(total_feats, dtype=np.float32)
    s_index      = {s: i for i, s in enumerate(_symptom_list)}

    for item in symptoms:
        if isinstance(item, dict):
            name     = _normalise_name(item.get('name', ''))
            duration = max(1, int(item.get('duration', 1) or 1))
        else:
            name     = _normalise_name(str(item))
            duration = 1

        if name in s_index:
            weight          = float(_symptom_weights.get(name, 1))
            vec[s_index[name]] = weight * np.log1p(duration)

    # ---- demographic slots (indices n_symptoms, +1, +2) ----
    age_idx    = n_symptoms
    male_idx   = n_symptoms + 1
    female_idx = n_symptoms + 2

    if age is not None:
        vec[age_idx] = float(min(max(age, 0), 120)) / 120.0
    else:
        vec[age_idx] = 0.35          # neutral prior (~42 yrs)

    if gender == 'male':
        vec[male_idx], vec[female_idx] = 1.0, 0.0
    elif gender == 'female':
        vec[male_idx], vec[female_idx] = 0.0, 1.0
    else:
        vec[male_idx] = vec[female_idx] = 0.5   # unknown

    return vec.reshape(1, -1)


def _top_contributions(vec: np.ndarray, top_n: int = 5) -> list:
    scores   = vec[0] * _feature_importances
    top_idx  = np.argsort(scores)[::-1]
    out = []
    for i in top_idx:
        if scores[i] > 0 and len(out) < top_n:
            out.append({
                'feature':    _feature_names[i],
                'value':      round(float(vec[0][i]),      4),
                'importance': round(float(_feature_importances[i]), 4),
            })
    return out


def predict_disease(
    symptoms: list,
    age: Optional[int]  = None,
    gender: Optional[str] = None,
) -> dict:
    """
    Predict the most likely disease.

    Parameters
    ----------
    symptoms : list of str  OR  list of {name, duration} dicts
    age      : patient age in years (0-120), or None
    gender   : 'male' | 'female' | None

    Returns
    -------
    {
        disease              : str,
        confidence           : float,
        top5                 : [{disease, confidence}, ...],
        feature_contributions: [{feature, value, importance}, ...]
    }
    """
    _load_artifacts()

    vec   = _build_vector(symptoms, age, gender)
    proba = _model.predict_proba(vec)[0]

    top5_idx = np.argsort(proba)[::-1][:5]
    top5 = [
        {
            'disease':    _label_encoder.classes_[i],
            'confidence': round(float(proba[i]), 4),
        }
        for i in top5_idx
    ]

    return {
        'disease':             top5[0]['disease'],
        'confidence':          top5[0]['confidence'],
        'top5':                top5,
        'feature_contributions': _top_contributions(vec),
    }


# -- Quick CLI test --------------------------------------------------------
if __name__ == '__main__':
    test = [
        {'name': 'itching',              'duration': 5},
        {'name': 'skin_rash',            'duration': 3},
        {'name': 'nodal_skin_eruptions', 'duration': 2},
    ]
    result = predict_disease(test, age=30, gender='male')
    print(f'Predicted disease : {result["disease"]}')
    print(f'Confidence        : {result["confidence"]:.2%}')
    print('\nTop 5:')
    for item in result['top5']:
        print(f'  {item["disease"]:<35} {item["confidence"]:.2%}')
    print('\nTop feature contributions:')
    for fc in result['feature_contributions']:
        print(f'  {fc["feature"]:<35}  val={fc["value"]:.3f}  imp={fc["importance"]:.4f}')
