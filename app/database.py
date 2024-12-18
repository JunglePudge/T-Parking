from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Путь к базе данных SQLite
BASE_DIR= os.path.abspath(os.path.dirname(__file__))
#DATABASE_URL = "sqlite:///./app/tparking.db"
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'tparking.db')}"

# Создание движка SQLAlchemy
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Создание базового класса для моделей
Base = declarative_base()

# Настройка сессии базы данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
