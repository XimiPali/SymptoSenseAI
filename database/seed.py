"""
database/seed.py
----------------
Reads the four CSV files from ../dataset/ and populates the MySQL database.

Run ONCE after creating the schema:
    cd database
    python seed.py

Requirements:
    pip install pandas mysql-connector-python sqlalchemy python-dotenv
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Allow importing backend modules
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+mysqlconnector://root:password@localhost:3306/healthcare_ai",
)

engine       = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"


def clean(val):
    if pd.isna(val): return None
    return str(val).strip() or None


def seed():
    db = SessionLocal()
    try:
        # ── Import models AFTER engine is ready ──
        from models import Disease, Symptom, DiseaseSymptom, Precaution

        # ── 1. Symptoms + severity ────────────────────────────────────────
        print("Seeding symptoms …")
        sev_df = pd.read_csv(DATASET_DIR / "Symptom-severity.csv")
        sev_df.columns = sev_df.columns.str.strip()
        sev_df["Symptom"] = sev_df["Symptom"].str.strip()

        symptom_map: dict[str, Symptom] = {}
        for _, row in sev_df.iterrows():
            name   = clean(row["Symptom"])
            weight = int(row["weight"]) if pd.notna(row["weight"]) else 1
            if not name: continue
            obj = db.query(Symptom).filter_by(name=name).first()
            if not obj:
                obj = Symptom(name=name, weight=weight)
                db.add(obj)
                db.flush()
            symptom_map[name] = obj

        # Also collect symptoms from dataset that may be missing from severity
        ds_df = pd.read_csv(DATASET_DIR / "dataset.csv")
        ds_df.columns = ds_df.columns.str.strip()
        symptom_cols = [c for c in ds_df.columns if c.startswith("Symptom_")]
        for col in symptom_cols:
            for val in ds_df[col].dropna().unique():
                name = str(val).strip()
                if name and name not in symptom_map:
                    obj = db.query(Symptom).filter_by(name=name).first()
                    if not obj:
                        obj = Symptom(name=name, weight=1)
                        db.add(obj)
                        db.flush()
                    symptom_map[name] = obj

        db.commit()
        print(f"  Symptoms inserted: {len(symptom_map)}")

        # ── 2. Diseases + descriptions ────────────────────────────────────
        print("Seeding diseases …")
        desc_df = pd.read_csv(DATASET_DIR / "symptom_Description.csv")
        desc_df.columns = desc_df.columns.str.strip()
        desc_df["Disease"] = desc_df["Disease"].str.strip()

        desc_map = dict(zip(desc_df["Disease"], desc_df["Description"]))

        disease_map: dict[str, Disease] = {}
        for disease_name in ds_df["Disease"].str.strip().unique():
            if not disease_name: continue
            obj = db.query(Disease).filter_by(name=disease_name).first()
            if not obj:
                obj = Disease(name=disease_name, description=desc_map.get(disease_name))
                db.add(obj)
                db.flush()
            disease_map[disease_name] = obj

        db.commit()
        print(f"  Diseases inserted: {len(disease_map)}")

        # ── 3. Disease–Symptom links ──────────────────────────────────────
        print("Seeding disease-symptom links …")
        inserted = 0
        for _, row in ds_df.iterrows():
            disease_name = str(row["Disease"]).strip()
            disease_obj  = disease_map.get(disease_name)
            if not disease_obj: continue
            for col in symptom_cols:
                val = clean(row[col])
                if not val: continue
                symptom_obj = symptom_map.get(val)
                if not symptom_obj: continue
                exists = db.query(DiseaseSymptom).filter_by(
                    disease_id=disease_obj.id, symptom_id=symptom_obj.id
                ).first()
                if not exists:
                    db.add(DiseaseSymptom(disease_id=disease_obj.id, symptom_id=symptom_obj.id))
                    inserted += 1
        db.commit()
        print(f"  Disease-symptom links inserted: {inserted}")

        # ── 4. Precautions ────────────────────────────────────────────────
        print("Seeding precautions …")
        prec_df = pd.read_csv(DATASET_DIR / "symptom_precaution.csv")
        prec_df.columns = prec_df.columns.str.strip()
        prec_df["Disease"] = prec_df["Disease"].str.strip()

        prec_inserted = 0
        for _, row in prec_df.iterrows():
            disease_name = str(row["Disease"]).strip()
            disease_obj  = disease_map.get(disease_name)
            if not disease_obj: continue
            for order in range(1, 5):
                col_name = f"Precaution_{order}"
                if col_name not in prec_df.columns: continue
                text = clean(row.get(col_name))
                if not text: continue
                exists = db.query(Precaution).filter_by(
                    disease_id=disease_obj.id, precaution_order=order
                ).first()
                if not exists:
                    db.add(Precaution(
                        disease_id=disease_obj.id,
                        precaution_order=order,
                        precaution_text=text,
                    ))
                    prec_inserted += 1
        db.commit()
        print(f"  Precautions inserted: {prec_inserted}")

        print("\n✅ Database seeded successfully!")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
