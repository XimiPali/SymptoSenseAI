"""
main.py
-------
FastAPI application entry point.

Start the server:
    cd backend
    uvicorn main:app --reload --port 8000

API docs available at: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import models  # noqa: F401 – ensures all models are registered before create_all

from routes.auth        import router as auth_router
from routes.diseases    import router as diseases_router
from routes.predictions import router as predictions_router
from routes.search      import router as search_router

# ── Create all tables if they don't already exist ──────────────────────────
Base.metadata.create_all(bind=engine)

# ── App factory ────────────────────────────────────────────────────────────
app = FastAPI(
    title="Healthcare AI Assistant",
    description="Disease prediction API powered by Machine Learning",
    version="1.0.0",
)

# ── CORS – allow the React dev-server and production origin ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ───────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(diseases_router)
app.include_router(predictions_router)
app.include_router(search_router)


@app.get("/", tags=["health"])
def health_check():
    return {"status": "ok", "message": "Healthcare AI API is running"}
