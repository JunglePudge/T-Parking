from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ParkingSpot
import os

router = APIRouter(tags=["Booking_park_spot"])


@router.get("/parking", response_class=HTMLResponse)
async def api_parking_page(request: Request):
    """Страница парковки"""
    session_user = request.cookies.get("session_user")
    if not session_user:
        # Перенаправляем на логин если пользователь не авторизован
        file_path = os.path.join("app", "templates", "login.html")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return HTMLResponse(content=html_content)
        return HTMLResponse(content="<h1>Login required</h1>", status_code=401)

    file_path = os.path.join("app", "templates", "parking.html")

    if not os.path.exists(file_path):
        return HTMLResponse(content="<h1>Parking page not found</h1>", status_code=404)

    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(content=html_content)


@router.get("/parking_status")
async def api_parking_status(db: Session = Depends(get_db)):
    """Получить текущее состояние парковки"""
    spots = db.query(ParkingSpot).all()
    return {
        "success": True,
        "parking_spots": [
            {"SpotID": s.SpotID, "Floor": s.Floor, "SpotNumber": s.SpotNumber, "IsBooked": s.IsBooked}
            for s in spots
        ],
    }


@router.post("/parking/book/{spot_id}")
async def book_spot(spot_id: int, db: Session = Depends(get_db)):
    """Забронировать парковочное место"""
    spot = db.query(ParkingSpot).filter(ParkingSpot.SpotID == spot_id).first()
    if not spot:
        return {"success": False, "error": "Место не найдено"}
    if spot.IsBooked:
        return {"success": False, "error": "Место уже занято"}

    spot.IsBooked = True
    db.commit()
    return {"success": True, "message": "Место забронировано"}


@router.post("/parking/unbook/{spot_id}")
async def unbook_spot(spot_id: int, db: Session = Depends(get_db)):
    """Снять бронь с парковочного места"""
    spot = db.query(ParkingSpot).filter(ParkingSpot.SpotID == spot_id).first()
    if not spot:
        return {"success": False, "error": "Место не найдено"}
    if not spot.IsBooked:
        return {"success": False, "error": "Место уже свободно"}

    spot.IsBooked = False
    db.commit()
    return {"success": True, "message": "Бронь снята"}