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
        # Разделяем ФИО на части
        parts = fio.split()
        if len(parts) != 3:
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "ФИО должно состоять из трех частей (имя, фамилия, отчество)"}
            )

        first_name, last_name, middle_name = parts

        # Проверка имени
        name_regex = r"^[А-ЯЁа-яё\- ]{2,40}$"
        if not re.match(name_regex, first_name):
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Неверный формат имени"}
            )

        # Проверка фамилии
        last_name_regex = r"^[А-ЯЁа-яё\- \.'()]{1,40}$"
        if not re.match(last_name_regex, last_name):
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Неверный формат фамилии"}
            )

        # Проверка отчества
        middle_name_regex = r"^[А-ЯЁа-яё\- ]{5,30}$"
        if not re.match(middle_name_regex, middle_name):
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Неверный формат отчества"}
            )

        # Проверка формата почты
        email_regex = r"^(?!\.)[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_regex, email):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Неверный формат почты"})

        # Проверка формата госномера
        gos_regex = r"^[АВЕКМНОРСТУХABEKMHOPCTYX][0-9]{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}(0[1-9]|10[1-9]|7[02]|[1-7][0-9]{2})$"
        if not re.match(gos_regex, gos):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Неверный формат госномера"})

        # Проверка пароля
        password_regex = r"^[A-Za-zА-Яа-яЁё0-9!@#$%^&*()_+=-]{8,64}$"
        if not re.match(password_regex, password):
            return templates.TemplateResponse("register.html", {"request": request, "error": "Пароль не соответствует требованиям"})
        if password != again:
            return templates.TemplateResponse("register.html", {"request": request, "error": "Пароли не совпадают"})

        # Проверка существующего пользователя
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Пользователь уже существует"}
            )

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

    # Если cookie с сессией пользователя нет (не авторизован), перенаправляем на страницу регистрации
    if not session_user:
        return RedirectResponse(url="/auth/register")

    # Если пользователь авторизован, отображаем страницу парковки
    return templates.TemplateResponse("parking.html", {"request": request})
