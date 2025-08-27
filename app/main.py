from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from app.api import routers

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Parking API")

# Подключаем все роутеры
for r in routers:
    app.include_router(r)

# Подключаем статику (HTML, CSS, JS, картинки)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
#app.mount("/templates", StaticFiles(directory="app/templates"), name="templates")