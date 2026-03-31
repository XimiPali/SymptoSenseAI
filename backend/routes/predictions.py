"""
routes/predictions.py  --  v2
------------------------------
Changes from v1:
  - PredictRequest.symptoms is now List[SymptomInput] instead of List[str]
    Each SymptomInput has  name  and optional  duration (days, default 1)
  - PredictRequest accepts optional  age  and  gender
    (falls back to the logged-in user profile if not supplied)
  - PredictResponse includes  top5  and  feature_contributions
  - Prediction record stores  age_at_prediction  and  gender_at_prediction
  - History parses both old (str) and new ({name,duration}) symptom formats
"""

import json
import sys
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models

AI_DIR = Path(__file__).resolve().parent.parent.parent / 'ai'
sys.path.insert(0, str(AI_DIR))

try:
    from predict import predict_disease   # type: ignore
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

router = APIRouter(tags=['predictions'])


# ---------- Pydantic schemas ----------

class SymptomInput(BaseModel):
    name:     str
    duration: int = 1   # days experiencing this symptom

    @field_validator('duration')
    @classmethod
    def clamp_duration(cls, v: int) -> int:
        return max(1, min(v, 365))   # 1-365 days

    @field_validator('name')
    @classmethod
    def clean_name(cls, v: str) -> str:
        return v.strip().lower().replace(' ', '_')


class PredictRequest(BaseModel):
    symptoms: List[SymptomInput]
    age:      Optional[int]  = None   # override user profile age
    gender:   Optional[str]  = None   # override user profile gender


class FeatureContribution(BaseModel):
    feature:    str
    value:      float
    importance: float


class Top5Item(BaseModel):
    disease:    str
    confidence: float


class PredictResponse(BaseModel):
    predicted_disease:    str
    confidence:           float
    description:          str
    precautions:          List[str]
    top5:                 List[Top5Item]
    feature_contributions: List[FeatureContribution]


class PredictionHistoryItem(BaseModel):
    id:               int
    symptoms_input:   List[Any]
    predicted_disease: str
    confidence:       float
    age_at_prediction:    Optional[int]
    gender_at_prediction: Optional[str]
    created_at:       str


# ---------- Helpers ----------

def _parse_symptoms_for_history(raw: str) -> list:
    data = json.loads(raw)
    if not data:
        return []
    # Old format was List[str]; new format is List[{name, duration}]
    if isinstance(data[0], str):
        return data
    return data   # return structured dicts as-is


# ---------- Endpoints ----------

@router.post('/api/predict', response_model=PredictResponse)
def predict(
    body: PredictRequest,
    db:   Session       = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not body.symptoms:
        raise HTTPException(status_code=400, detail='At least one symptom is required')

    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail='AI model not available. Run  python ai/ai_model.py  first.',
        )

    # Use user profile demographics as fallback
    age    = body.age    if body.age    is not None else current_user.age
    gender = body.gender if body.gender is not None else current_user.gender

    # Convert Pydantic models -> plain dicts for predict.py
    symptom_dicts = [{'name': s.name, 'duration': s.duration} for s in body.symptoms]

    result       = predict_disease(symptom_dicts, age=age, gender=gender)
    disease_name = result['disease']
    confidence   = result['confidence']

    # Fetch description + precautions from DB
    disease = db.query(models.Disease).filter(
        models.Disease.name.ilike(disease_name)
    ).first()

    description     = disease.description if disease else 'No description available.'
    precautions_raw = []
    if disease:
        precautions_raw = [
            p.precaution_text
            for p in sorted(disease.precautions, key=lambda x: x.precaution_order)
        ]

    # Persist prediction
    record = models.Prediction(
        user_id              = current_user.id,
        symptoms_input       = json.dumps(symptom_dicts),
        age_at_prediction    = age,
        gender_at_prediction = gender,
        predicted_disease    = disease_name,
        confidence           = confidence,
    )
    db.add(record)
    db.commit()

    return PredictResponse(
        predicted_disease     = disease_name,
        confidence            = confidence,
        description           = description,
        precautions           = precautions_raw,
        top5                  = [Top5Item(**t) for t in result.get('top5', [])],
        feature_contributions = [
            FeatureContribution(**fc)
            for fc in result.get('feature_contributions', [])
        ],
    )


@router.get('/api/predictions', response_model=List[PredictionHistoryItem])
def prediction_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    records = (
        db.query(models.Prediction)
        .filter(models.Prediction.user_id == current_user.id)
        .order_by(models.Prediction.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        PredictionHistoryItem(
            id                   = r.id,
            symptoms_input       = _parse_symptoms_for_history(r.symptoms_input),
            age_at_prediction    = r.age_at_prediction,
            gender_at_prediction = r.gender_at_prediction,
            predicted_disease    = r.predicted_disease,
            confidence           = r.confidence,
            created_at           = r.created_at.isoformat(),
        )
        for r in records
    ]
