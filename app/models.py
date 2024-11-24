from sqlalchemy import Column, Integer, String, Text
from app.database import Base

class User(Base):
    __tablename__ = "users"

    UserID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    FullName = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    CarPlate = Column(String, nullable=True)
    status = Column(String, default="standard")
