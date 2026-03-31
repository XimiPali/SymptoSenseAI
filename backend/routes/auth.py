"""
routes/auth.py  --  v2
-----------------------
Changes from v1:
  - RegisterRequest: added  gender (Literal male/female)  and  age (0-120)
  - UserResponse   : exposes  gender  and  age
  - register()     : stores gender + age; validates age range
"""

from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from database import get_db
from auth import (
    hash_password, verify_password,
    create_access_token, get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
import models

router = APIRouter(prefix='/api/auth', tags=['auth'])


# ---------- Pydantic schemas ----------

class RegisterRequest(BaseModel):
    username: str
    email:    EmailStr
    password: str
    gender:   Literal['male', 'female']
    age:      int

    @field_validator('age')
    @classmethod
    def validate_age(cls, v: int) -> int:
        if not (0 <= v <= 120):
            raise ValueError('Age must be between 0 and 120')
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = 'bearer'


class UserResponse(BaseModel):
    id:       int
    username: str
    email:    str
    gender:   str
    age:      int

    model_config = {'from_attributes': True}


# ---------- Endpoints ----------

@router.post('/register', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == body.username).first():
        raise HTTPException(status_code=400, detail='Username already taken')
    if db.query(models.User).filter(models.User.email == body.email).first():
        raise HTTPException(status_code=400, detail='Email already registered')

    user = models.User(
        username=body.username,
        email=body.email,
        password=hash_password(body.password),
        gender=body.gender,
        age=body.age,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post('/login', response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect username or password',
        )
    token = create_access_token(
        {'sub': user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {'access_token': token, 'token_type': 'bearer'}


@router.get('/me', response_model=UserResponse)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
