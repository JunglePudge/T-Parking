from symbol import return_stmt
from fastapi import FastAPI, Depends, Request, Form, HTTPException, Response, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette.responses import JSONResponse
from app.database import engine, get_db, Base
from app.models import User, ParkingSpot
from passlib.context import CryptContext
import uvicorn
import os

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

BASE_DIR= os.path.abspath(os.path.dirname(__file__))
# Настройка приложения
app = FastAPI()
templates = Jinja2Templates(directory=f"{os.path.join(BASE_DIR, 'templates')}")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory= f"{os.path.join(BASE_DIR, 'static')}"), name="static")

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Функция для создания начальных парковочных мест
def create_initial_parking_spots(db: Session):#это метод типо как инициализировать места все, создать их в принципе
    # Проверяем, существуют ли уже парковочные места
    existing_spots = db.query(ParkingSpot).all()
    if not existing_spots:
        # Создаем парковочные места на 1-м этаже
        for i in range(1, 13):
            spot = ParkingSpot(Floor=1, SpotNumber=i)
            db.add(spot)
        # Создаем парковочные места на 2-м этаже
        for i in range(1, 13):
            spot = ParkingSpot(Floor=2, SpotNumber=i)
            db.add(spot)
        # Создаем парковочные места на 3-м этаже
        for i in range(1, 13):
            spot = ParkingSpot(Floor=3, SpotNumber=i)
            db.add(spot)
        db.commit()

# Создание начальных парковочных мест при запуске приложения
@app.on_event("startup")
async def startup_event():
    with Session(engine) as session:
        create_initial_parking_spots(session)

@app.get("/", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    """Главная страница с кнопками для перехода на авторизацию и регистрацию"""
    session_user = request.cookies.get("session_user")
    return templates.TemplateResponse("index.html", {"request": request, "session_user": session_user})

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
async def choose_park(request: Request, db: Session = Depends(get_db)):
    """Страница выбора парковки (доступна после авторизации)"""
    session_user = request.cookies.get("session_user")

    # Если cookie с сессией пользователя нет (не авторизован), перенаправляем на страницу регистрации
    if not session_user:
        return RedirectResponse(url="/auth/register")

    user_id = int(session_user)

    # Получение информации о забронированном месте пользователя
    booked_spot = db.query(ParkingSpot).filter(ParkingSpot.UserID == user_id, ParkingSpot.IsBooked == True).first()

    # Получение всех парковочных мест
    parking_spots = db.query(ParkingSpot).all()

    return templates.TemplateResponse("parking.html", {"request": request, "parking_spots": parking_spots, "booked_spot": booked_spot})

#переходы по этажам
@app.get("/parking", response_class=HTMLResponse)
async def parking_floor(request: Request):
    """Страница 1-го этажа парковки"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    return templates.TemplateResponse("parking.html", {"request": request})

@app.get("/parking2", response_class=HTMLResponse)
async def parking_floor2(request: Request):
    """Страница 2-го этажа парковки"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    return templates.TemplateResponse("parking2.html", {"request": request})

@app.get("/parking3", response_class=HTMLResponse)
async def parking_floor3(request: Request):
    """Страница 3-го этажа парковки"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        return RedirectResponse(url="/auth/register")

    return templates.TemplateResponse("parking3.html", {"request": request})

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


# Обработка бронирования парковочного места
@app.post("/book_spot")
async def book_spot(
        request: Request,
        db: Session = Depends(get_db),
        spot_id: int = Form(...),
        user_id: int = Form(...)
):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    if int(session_user) != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    existing_booking = db.query(ParkingSpot).filter(ParkingSpot.UserID == user_id, ParkingSpot.IsBooked == True).first()
    if existing_booking:
        return JSONResponse(status_code=400, content={"error": "Вы уже забронировали парковочное место."})

    parking_spot = db.query(ParkingSpot).filter(ParkingSpot.SpotID == spot_id).first()
    if not parking_spot:
        raise HTTPException(status_code=404, detail="Парковочное место не найдено")

    parking_spot.UserID = user_id
    parking_spot.IsBooked = True
    db.commit()

    return JSONResponse(content={"message": "Парковочное место успешно забронировано", "spot_id": spot_id})


# Обработка освобождения парковочного места
@app.post("/unbook_spot")
async def unbook_spot(
        request: Request,
        db: Session = Depends(get_db),
        spot_id: int = Form(...),
        user_id: int = Form(...)
):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    if int(session_user) != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    parking_spot = db.query(ParkingSpot).filter(ParkingSpot.SpotID == spot_id).first()
    #if not parking_spot or not parking_spot.IsBooked or parking_spot.UserID != user_id:
    #    raise HTTPException(status_code=400, detail="Невозможно освободить это место.")

    parking_spot.UserID = None
    parking_spot.IsBooked = False
    db.commit()

    return JSONResponse(content={"message": "Парковочное место успешно освобождено", "spot_id": spot_id})


# Получение состояния всех парковочных мест
@app.get("/choose_park")
async def choose_park(request: Request, db: Session = Depends(get_db)):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    user_id = int(session_user)

    parking_spots = db.query(ParkingSpot).all()

    # Формируем данные для отправки на клиент
    parking_data = [
        {
            "SpotID": spot.SpotID,
            "IsBooked": spot.IsBooked,
            "UserID": spot.UserID
        }
        for spot in parking_spots
    ]

    return JSONResponse(content={"parking_spots": parking_data})


@app.get("/parking", response_class=HTMLResponse)
async def choose_park(request: Request, db: Session = Depends(get_db)):
    """Страница выбора парковки (доступна после авторизации)"""
    session_user = request.cookies.get("session_user")

    # Если cookie с сессией пользователя нет (не авторизован), перенаправляем на страницу регистрации
    if not session_user:
        return RedirectResponse(url="/auth/register")

    user_id = int(session_user)

    # Получение всех парковочных мест
    parking_spots = db.query(ParkingSpot).all()

    # Создание матрицы значений для парковочных мест
    parking_matrix = [[0 for _ in range(12)] for _ in range(3)]
    for spot in parking_spots:
        if spot.IsBooked:
            parking_matrix[spot.Floor - 1][spot.SpotNumber - 1] = 1

    return templates.TemplateResponse("parking.html", {"request": request, "parking_matrix": parking_matrix})


@app.get("/test-db")
async def get_table_data(table_name: str):
    """
    Выгрузка данных из указанной таблицы.
    :param table_name: Название таблицы, данные которой нужно выгрузить.
    """
    try:
        with engine.connect() as connection:
            # Формируем SQL-запрос для получения всех данных из таблицы
            query = text(f"SELECT * FROM {table_name}")
            result = connection.execute(query).mappings().all()

            # Преобразуем данные в список словарей
            rows = [dict(row) for row in result]
        return {"table": table_name, "data": rows}
    except Exception as e:
        # Если таблицы не существует или другая ошибка
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")

@app.put("/test-record")
async def test_db(
        record_id: int,

):
    try:
        with engine.connect() as conn:
            query = text(f"""
                UPDATE parking_spots
                SET UserID = NULL, IsBooked = 0
                Where SpotID = :record_id
            """)
            result = conn.execute(query, {"record_id": record_id})
            if result.rowcount == 0:
                raise HTTPException(status_code=404)
            conn.commit()
        return {"status":"success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)