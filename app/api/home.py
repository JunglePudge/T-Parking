from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import os

router = APIRouter(tags=["Home"])

@router.get("/", response_class=HTMLResponse)
async def api_index(request: Request):
    """Главная страница"""
    # Читаем HTML файл и возвращаем его содержимое
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)