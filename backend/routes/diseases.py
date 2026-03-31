"""
routes/diseases.py
------------------
/api/diseases/          – list all diseases
/api/diseases/{name}    – get disease detail (description + precautions)
/api/symptoms/          – list all known symptoms (used for autocomplete)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db
from auth import get_current_user
import models

router = APIRouter(tags=["diseases"])


# ---------- Pydantic schemas ----------

class SymptomOut(BaseModel):
    id: int
    name: str
    weight: int
    model_config = {"from_attributes": True}


class PrecautionOut(BaseModel):
    precaution_order: int
    precaution_text: str
    model_config = {"from_attributes": True}


class DiseaseOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    model_config = {"from_attributes": True}


class DiseaseDetail(DiseaseOut):
    precautions: List[PrecautionOut]
    symptoms: List[str]


# ---------- Endpoints ----------

@router.get("/api/symptoms", response_model=List[SymptomOut])
def list_symptoms(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(models.Symptom).order_by(models.Symptom.name).all()


@router.get("/api/diseases", response_model=List[DiseaseOut])
def list_diseases(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(models.Disease).order_by(models.Disease.name).all()


@router.get("/api/diseases/{disease_name}", response_model=DiseaseDetail)
def get_disease(
    disease_name: str,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    disease = (
        db.query(models.Disease)
        .filter(models.Disease.name.ilike(disease_name))
        .first()
    )
    if not disease:
        raise HTTPException(status_code=404, detail="Disease not found")

    precautions = (
        db.query(models.Precaution)
        .filter(models.Precaution.disease_id == disease.id)
        .order_by(models.Precaution.precaution_order)
        .all()
    )
    symptom_names = [ds.symptom.name for ds in disease.symptoms]

    return DiseaseDetail(
        id=disease.id,
        name=disease.name,
        description=disease.description,
        precautions=precautions,
        symptoms=symptom_names,
    )
