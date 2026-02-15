from fastapi import APIRouter
from app.api.v1.endpoints import editor

api_router = APIRouter()

api_router.include_router(editor.router, prefix="/editor")
