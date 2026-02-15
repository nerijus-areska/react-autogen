from typing import Annotated, AsyncGenerator

from app.services.editor_service import EditorService


async def get_editor_service() -> EditorService:
    return EditorService()
