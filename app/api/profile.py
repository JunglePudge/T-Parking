from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from pydantic import BaseModel

router = APIRouter(tags=["Profile"])

class ProfileUpdateRequest(BaseModel):
    fio: str
    gos: str
    email: str
    password: str


@router.get("/profile")
async def api_profile_page(request: Request):
    session_user = request.cookies.get("session_user")
    if not session_user:
        return {"success": False, "redirect": "/templates/login.html"}
    return {"success": True, "redirect": "/templates/profile.html"}


@router.post("/profile/update")
async def api_update_profile(req: ProfileUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"success": False, "error": "Пользователь не найден"}

    user.FullName = req.fio
    user.CarPlate = req.gos
    user.email = req.email
    if req.password:
        user.password = req.password

    db.commit()
    return {"success": True, "message": "Профиль обновлен"}
