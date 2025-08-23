from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from app.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    UserID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    FullName = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    CarPlate = Column(String, nullable=True)
    status = Column(String, default="standard")

    parking_spots = relationship("ParkingSpot", back_populates="user")

class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    SpotID = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Floor = Column(Integer, nullable=False)
    SpotNumber = Column(Integer, nullable=False)
    UserID = Column(Integer, ForeignKey('users.UserID'), nullable=True)
    IsBooked = Column(Boolean, default=False)

    user = relationship("User", back_populates="parking_spots")