from fastapi import FastAPI, Depends, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.database import Base, engine
from app.models import Base, User
from passlib.context import CryptContext

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Настройка приложения
app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    """Главная страница с кнопками для перехода на авторизацию и регистрацию"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Отображение страницы регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/auth/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    fio: str = Form(...),
    email: str = Form(...),
    gos: str = Form(...),
    password: str = Form(...),
    again: str = Form(...)
):
    import re

    try:
        # Проверка совпадения паролей
        if password != again:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Пароли не совпадают"})

        # Проверка формата почты
        email_regex = r"^[^@]+@[^@]+\.[^@]+$"
        if not re.match(email_regex, email):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Неверный формат почты"})

        # Проверка формата госномера
        gos_regex = r"^[А-Я][0-9]{3}[А-Я]{2}[0-9]{2,3}$"
        if not re.match(gos_regex, gos):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Неверный формат госномера"})

        # Проверка существующего пользователя
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Пользователь уже существует"})

        # Хэширование пароля и создание пользователя
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

        # Автоматическая авторизация (создание токена и cookie)
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session_user", value=str(new_user.UserID), httponly=True)
        return response

    except Exception as e:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": f"Ошибка сервера: {str(e)}"}
        )



@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Отображение страницы авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/auth/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...)
):
    """Обработка формы авторизации"""
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Неверные учетные данные"}
        )

    # Создание cookie сессии
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(key="session_user", value=str(user.UserID), httponly=True)
    return response

@app.get("/parking", response_class=HTMLResponse)
async def choose_park(request: Request):
    """Страница выбора парковки (доступна после авторизации)"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")
    return templates.TemplateResponse("parking.html", {"request": request})
