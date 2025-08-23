from fastapi import FastAPI, Depends, Request, Form, HTTPException, Response, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.database import engine, get_db
from app.database import Base, engine, SessionLocal
from app.models import Base, User, ParkingSpot
from passlib.context import CryptContext
import os
from pydantic import BaseModel
from contextlib import asynccontextmanager

class BookRequest(BaseModel):
    spot_id: int

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

# Функция для создания начальных парковочных мест
def create_initial_parking_spots(db: Session):
    existing_spots = db.query(ParkingSpot).all()
    if not existing_spots:
        for floor in range(1, 4):
            for i in range(1, 13):
                spot = ParkingSpot(Floor=floor, SpotNumber=i)
                db.add(spot)
        db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    with Session(engine) as session:
        create_initial_parking_spots(session)
    yield
    # Shutdown logic (опционально)

# Настройка приложения с lifespan
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)



@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    """Главная страница с вариантами для авторизованных и неавторизованных пользователей"""
    session_user = request.cookies.get("session_user")

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "session_user": session_user}
    )



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


@app.get("/parking_status")
async def get_parking_status(request: Request, db: Session = Depends(get_db)):
    try:
        session_user = request.cookies.get("session_user")
        user_id = int(session_user) if session_user else None

        # Получаем все парковочные места
        parking_spots = db.query(ParkingSpot).all()

        # Форматируем данные для отправки
        spots_data = []
        for spot in parking_spots:
            spots_data.append({
                "SpotID": spot.SpotID,
                "Floor": spot.Floor,
                "SpotNumber": spot.SpotNumber,
                "IsBooked": spot.IsBooked,
                "UserID": spot.UserID
            })

        return JSONResponse(content={
            "parking_spots": spots_data,
            "user_id": user_id
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/parking", response_class=HTMLResponse)
async def parking_floor1(request: Request, db: Session = Depends(get_db)):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    user_id = int(session_user)
    parking_spots = db.query(ParkingSpot).filter(ParkingSpot.Floor == 1).all()

    return templates.TemplateResponse(
        "parking.html",
        {
            "request": request,
            "parking_spots": parking_spots,
            "user_id": user_id
        }
    )


@app.get("/parking2", response_class=HTMLResponse)
async def parking_floor2(request: Request, db: Session = Depends(get_db)):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    user_id = int(session_user)
    parking_spots = db.query(ParkingSpot).filter(ParkingSpot.Floor == 2).all()

    return templates.TemplateResponse(
        "parking2.html",
        {
            "request": request,
            "parking_spots": parking_spots,
            "user_id": user_id
        }
    )


@app.get("/parking3", response_class=HTMLResponse)
async def parking_floor3(request: Request, db: Session = Depends(get_db)):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    user_id = int(session_user)
    parking_spots = db.query(ParkingSpot).filter(ParkingSpot.Floor == 3).all()

    return templates.TemplateResponse(
        "parking3.html",
        {
            "request": request,
            "parking_spots": parking_spots,
            "user_id": user_id
        }
    )


@app.get("/auth/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """Отображение страницы профиля"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/", status_code=303)

    user = db.query(User).filter(User.UserID == session_user).first()
    if not user:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@app.post("/auth/profile/update", response_class=HTMLResponse)
async def update_profile(
        request: Request,
        db: Session = Depends(get_db),
        fio: str = Form(...),
        gos: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        number: str = Form(...),
        data: str = Form(...)
):
    """Обновление данных профиля"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    user = db.query(User).filter(User.UserID == session_user).first()
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)

    user.FullName = fio
    user.CarPlate = gos
    user.email = email

    # Хэширование нового пароля перед сохранением
    if password:
        user.password = pwd_context.hash(password)

    user.phone_number = number
    user.birth_date = data
    db.commit()
    return RedirectResponse(url="/auth/profile", status_code=303)


@app.post("/auth/profile/photo/upload")
async def upload_photo(file: UploadFile = File(...)):
    """Загрузка фото профиля"""
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"filename": file.filename}


@app.post("/auth/profile/photo/delete")
async def delete_photo():
    """Удаление фото профиля"""
    photo_path = os.path.join(UPLOAD_DIR, "photo.png")  # Замените именем текущего файла
    if os.path.exists(photo_path):
        os.remove(photo_path)
    return {"message": "Фотография удалена"}


@app.get("/logout", response_class=RedirectResponse)
async def logout(response: RedirectResponse):
    """Выход из профиля"""
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("session_user", httponly=True)
    return response


@app.post("/book_spot")
async def book_spot(
        book_req: BookRequest,
        request: Request,
        db: Session = Depends(get_db),
):
    try:
        session_user = request.cookies.get("session_user")
        if not session_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = int(session_user)

        # Проверяем, не имеет ли пользователь уже забронированного места
        existing_booking = db.query(ParkingSpot).filter(
            ParkingSpot.UserID == user_id,
            ParkingSpot.IsBooked == True
        ).first()
        if existing_booking:
            raise HTTPException(
                status_code=400,
                detail="У вас уже есть забронированное место"
            )

        parking_spot = db.query(ParkingSpot).filter(
            ParkingSpot.SpotID == book_req.spot_id
        ).first()
        if not parking_spot:
            raise HTTPException(status_code=404, detail="Место не найдено")

        if parking_spot.IsBooked:
            raise HTTPException(status_code=400, detail="Место уже забронировано")

        # Бронируем место
        parking_spot.IsBooked = True
        parking_spot.UserID = user_id
        db.commit()

        return {"message": "Место успешно забронировано"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")


@app.post("/unbook_spot")
async def unbook_spot(
        book_req: BookRequest,
        request: Request,
        db: Session = Depends(get_db),
):
    try:
        session_user = request.cookies.get("session_user")
        if not session_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        user_id = int(session_user)

        parking_spot = db.query(ParkingSpot).filter(
            ParkingSpot.SpotID == book_req.spot_id
        ).first()
        if not parking_spot:
            raise HTTPException(status_code=404, detail="Место не найдено")

        # Проверяем, что пользователь отменяет свое бронирование
        if parking_spot.UserID != user_id:
            raise HTTPException(
                status_code=403,
                detail="Вы можете отменять только свои бронирования"
            )

        parking_spot.IsBooked = False
        parking_spot.UserID = None
        db.commit()

        return {"message": "Бронирование отменено"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")