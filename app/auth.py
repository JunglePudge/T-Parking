# app/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models import User
from app.database import get_db
from pydantic import BaseModel
from passlib.context import CryptContext

#Создание маршрутизатора и контекста паролей
router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RegisterUser(BaseModel):
    username: str
    email: str
    password: str

class LoginUser(BaseModel):
    username: str
    password: str

#регистрация пользователя
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: RegisterUser, db: Session = Depends(get_db)):
    # Проверяем, что пользователь не существует
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Создаем нового пользователя
    hashed_password = pwd_context.hash(user.password)
    new_user = User(username=user.username, email=user.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"msg": "User registered successfully"}

#Авторизация пользователя
@router.post("/login")
def login_user(user: LoginUser, db: Session = Depends(get_db)):
    # Ищем пользователя в базе данных
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not db_user.verify_password(user.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    return {"msg": "Login successful"}
