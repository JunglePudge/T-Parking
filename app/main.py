from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.models import Base, User
from app.auth import pwd_context
from app.auth import router as auth_router

# Создаем таблицы в базе данных, если их еще нет
Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

# Подключаем маршруты для авторизации и регистрации
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    """Главная страница с кнопками для перехода на авторизацию и регистрацию"""
    return templates.TemplateResponse("index.html", {"request": request})

# Новый маршрут для страницы входа
@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Новый маршрут для страницы регистрации
@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})