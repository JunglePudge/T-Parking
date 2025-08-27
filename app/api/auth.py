from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from passlib.context import CryptContext
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


@router.get("/login")
async def api_login_page(request: Request):
    return {"success": True, "redirect": "/templates/login.html"}


@router.post("/login")
async def api_login(login_req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_req.email).first()
    if not user or not pwd_context.verify(login_req.password, user.password):
        return {"success": False, "error": "Неверные учетные данные"}
    return {
        "success": True,
        "user_id": user.UserID,
        "redirect": "/templates/profile.html"
    }


@router.get("/logout")
async def api_logout():
    return {"success": True, "redirect": "/templates/login.html"}
