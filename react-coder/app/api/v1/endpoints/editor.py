from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from app.core.exceptions import PortInUseError
from app.workflows.base import LLMParseError
import logging
from app.api import deps
from app.services.editor_service import EditorService
from app.core.config import settings
EditorServiceDep = Annotated[
    EditorService, Depends(deps.get_editor_service)
]

router = APIRouter()

logger = logging.getLogger(__name__)
# --- Request/Response Models ---

class InitSessionRequest(BaseModel):
    project_name: str
    run_app: bool = False  # npm run dev in temp directory
    port: int = 3001  # only if run_app is True
    workflow: Optional[str] = None  # e.g. "simple_modification", "explorative_modification"

class InitSessionResponse(BaseModel):
    session_id: str
    app_url: Optional[str] = None
    model_used: str = settings.LLM_MODEL
    

class ChatRequest(BaseModel):
    session_id: str
    instruction: str

class DiffEntry(BaseModel):
    """
    [cite_start]Strictly follows the output format required by the assignment [cite: 31-35].
    """
    filename: str
    diff: str

class ChatResponse(BaseModel):
    changes: List[DiffEntry]
    input_tokens: int
    output_tokens: int
    workflow: str

class StopSessionRequest(BaseModel):
    session_id: str

EditorServiceDep = Annotated[
    EditorService, Depends(deps.get_editor_service)
]

@router.post("/init", response_model=InitSessionResponse)
async def init_session(
    service: EditorServiceDep,
    request: InitSessionRequest
):
    """
    Copies the target project to a temp directory and optionally starts it.
    """
    try:
        session_data = await service.initialize_session(
            project_name=request.project_name,
            run_app=request.run_app,
            port=request.port,
            workflow=request.workflow,
        )
        session_data["model_used"] = settings.LLM_MODEL
        return session_data
    except FileNotFoundError as e:
        logger.error(f"Project not found: {request.project_name}")
        raise HTTPException(status_code=400, detail=f"Project not found: {request.project_name}")
    except PortInUseError as e:
        logger.error(f"Port {request.port} is already in use")
        raise HTTPException(status_code=400, detail=f"Port {request.port} is already in use")
    except Exception as e:
        logger.error(f"Failed to init session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to init session: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    service: EditorServiceDep,
    request: ChatRequest
):
    """
    1. Apply user instruction to the session's codebase.
    2. Generate Git-style diffs.
    3. Return structured JSON.
    """
    try:
        changes, input_tokens, output_tokens, workflow = await service.process_instruction(
            session_id=request.session_id,
            instruction=request.instruction
        )
        return ChatResponse(
            changes=changes,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            workflow=workflow,
        )
    except ValueError as e:
        # Usually happens if session_id is invalid/expired
        logger.error(f"Error processing instruction: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except LLMParseError as e:
        logger.warning(f"LLM parse error: {e}")
        raise HTTPException(
            status_code=422,
            detail="The AI returned invalid output. Please try again.",
        )
    except Exception as e:
        logger.error(f"Error processing instruction: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@router.post("/stop")
async def stop_session(
    service: EditorServiceDep,
    request: StopSessionRequest
):
    """
    Cleans up the temp directory and kills any running background processes (npm start).
    """
    try:
        await service.cleanup_session(session_id=request.session_id)
        return {"status": "success", "message": f"Session {request.session_id} cleaned up."}
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")