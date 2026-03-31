"""
models.py  --  v2
-----------------
SQLAlchemy ORM models.
Changes from v1:
  - User: added  gender (ENUM male/female)  and  age (INT)
  - Prediction: added  age_at_prediction  and  gender_at_prediction
"""

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SAEnum,
    Float, ForeignKey, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = 'users'

    id         = Column(Integer, primary_key=True, index=True)
    username   = Column(String(50),  unique=True, nullable=False, index=True)
    email      = Column(String(120), unique=True, nullable=False, index=True)
    password   = Column(String(255), nullable=False)
    gender     = Column(SAEnum('male', 'female', name='gender_enum'), nullable=False)
    age        = Column(Integer, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    predictions = relationship('Prediction', back_populates='user')


class Disease(Base):
    __tablename__ = 'diseases'

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)

    symptoms    = relationship('DiseaseSymptom', back_populates='disease')
    precautions = relationship('Precaution',     back_populates='disease')


class Symptom(Base):
    __tablename__ = 'symptoms'

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), unique=True, nullable=False, index=True)
    weight     = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    diseases   = relationship('DiseaseSymptom', back_populates='symptom')


class DiseaseSymptom(Base):
    __tablename__  = 'disease_symptoms'
    __table_args__ = (UniqueConstraint('disease_id', 'symptom_id'),)

    id         = Column(Integer, primary_key=True, index=True)
    disease_id = Column(Integer, ForeignKey('diseases.id'), nullable=False)
    symptom_id = Column(Integer, ForeignKey('symptoms.id'), nullable=False)

    disease = relationship('Disease', back_populates='symptoms')
    symptom = relationship('Symptom', back_populates='diseases')


class Precaution(Base):
    __tablename__ = 'precautions'

    id               = Column(Integer, primary_key=True, index=True)
    disease_id       = Column(Integer, ForeignKey('diseases.id'), nullable=False)
    precaution_order = Column(Integer, nullable=False)
    precaution_text  = Column(String(255), nullable=False)

    disease = relationship('Disease', back_populates='precautions')


class Prediction(Base):
    __tablename__ = 'predictions'

    id                   = Column(Integer, primary_key=True, index=True)
    user_id              = Column(Integer, ForeignKey('users.id'), nullable=False)
    symptoms_input       = Column(Text, nullable=False)   # JSON [{name, duration}]
    age_at_prediction    = Column(Integer)                # patient age at prediction time
    gender_at_prediction = Column(String(10))             # 'male' or 'female'
    predicted_disease    = Column(String(100), nullable=False)
    confidence           = Column(Float, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)

    user = relationship('User', back_populates='predictions')
