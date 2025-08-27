import re
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from passlib.context import CryptContext
from pydantic import BaseModel

router = APIRouter(tags=["Registration"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    fio: str
    email: str
    gos: str
    password: str
    again: str


@router.get("/register")
async def api_register_page():
    """Страница регистрации"""
    return {"success": True, "redirect": "/static/register.html"}


@router.post("/register")
async def api_register(req: RegisterRequest, db: Session = Depends(get_db)):
    """Регистрация нового пользователя с расширенной валидацией"""

    fio = req.fio.strip()
    email = req.email.strip().lower()
    gos = req.gos.strip().upper()
    password = req.password
    again = req.again

    # --- Проверки на пустые поля ---
    if not fio or not email or not gos or not password or not again:
        return {"success": False, "error": "registration_error", "message" : "Все поля должны быть заполнены"}

    # --- Проверка ФИО ---
    parts = fio.split()
    if len(parts) != 3:
        return {"success": False,  "error": "registration_error", "message": "ФИО должно состоять из трёх частей (фамилия, имя, отчество)"}

    last_name, first_name, middle_name = parts

    if not re.match(r"^[А-ЯЁа-яё\- ]{2,40}$", first_name):
        return {"success": False, "error": "registration_error", "message": "Неверный формат имени"}
    if not re.match(r"^[А-ЯЁа-яё\- \.'()]{1,40}$", last_name):
        return {"success": False, "error": "registration_error", "message": "Неверный формат фамилии"}
    if not re.match(r"^[А-ЯЁа-яё\- ]{5,30}$", middle_name):
        return {"success": False, "error": "registration_error", "message": "Неверный формат отчества"}

    # --- Проверка email ---
    if not re.match(r"^(?!\.)[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        return {"success": False, "error": "registration_error", "message": "Неверный формат почты"}

    # --- Проверка госномера (российский + латиница) ---
    gos_regex = r"^[АВЕКМНОРСТУХABEKMHOPCTYX][0-9]{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}(0[1-9]|10[1-9]|7[02]|[1-7][0-9]{2})$"
    if not re.match(gos_regex, gos):
        return {"success": False, "error": "registration_error", "message": "Неверный формат госномера"}

    # --- Проверка пароля ---
    password_regex = r"^[A-Za-zА-Яа-яЁё0-9!@#$%^&*()_+=-]{8,64}$"
    if not re.match(password_regex, password):
        return {
            "success": False,
            "error": "registration_error", "message": "Пароль должен быть от 8 до 64 символов и содержать только буквы, цифры и спецсимволы"
        }
    if password != again:
        return {"success": False, "error": "registration_error", "message": "Пароли не совпадают"}

    # --- Проверка существующего пользователя ---
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return {"success": False, "error": "registration_error", "message": "Пользователь с таким email уже существует"}

    # --- Создание пользователя ---
    hashed_password = pwd_context.hash(password)
    new_user = User(
        FullName=fio,
        email=email,
        password=hashed_password,
        CarPlate=gos,
        status="standard"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "success": True,
        "user_id": new_user.UserID,
        "redirect": "/static/login.html"
    }
