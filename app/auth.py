from fastapi import APIRouter, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app.database import get_db
from app.models import User
import jwt
import datetime

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your_secret_key"

# Регистрация пользователя
@router.post("/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    db: Session = Depends(get_db),
    fullname: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    carplate: str = Form(None),
):
    # Проверка совпадения паролей
    if password != confirm_password:
        return {"error": "Пароли не совпадают"}

    # Проверка существующего пользователя
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        return {"error": "Пользователь с таким email уже существует"}

    # Хэширование пароля
    hashed_password = pwd_context.hash(password)
    new_user = User(
        FullName=fullname,
        email=email,
        password=hashed_password,
        CarPlate=carplate,
        status="standard",
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/auth/login", status_code=303)

# Авторизация пользователя
@router.post("/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password):
        return {"error": "Неверные учетные данные"}

    # Генерация токена
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    token = jwt.encode({"sub": user.UserID, "exp": expiration}, SECRET_KEY, algorithm="HS256")

    # Сохранение токена в cookie
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return response

# Проверка аутентификации
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Необходимо войти в систему")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = db.query(User).filter(User.UserID == payload["sub"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Срок действия токена истек")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Неверный токен")