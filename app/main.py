# app/main.py
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import Base, User
from app.auth import pwd_context
from app.auth import router as auth_router

# Создаем таблицы в базе данных, если их еще нет
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Подключаем статические файлы для доступа к /static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем маршруты для авторизации и регистрации
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    """Главная страница с кнопками для перехода на авторизацию и регистрацию"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница авторизации"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/auth/register", response_class=HTMLResponse)
async def register_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...)
):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already registered"})

    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return RedirectResponse(url="/auth/login", status_code=303)

@app.post("/auth/login", response_class=HTMLResponse)
async def login_user(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    password: str = Form(...)
):
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user or not db_user.verify_password(password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Incorrect username or password"})

    return RedirectResponse(url="/", status_code=303)
