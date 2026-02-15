from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from app.core.config import settings
from app.core.exceptions import AppError
from app.api.v1.api import api_router

import logging

# Third-party loggers (openai, httpx, etc.) stay at INFO; only our app logs DEBUG
logging.basicConfig(level=logging.INFO)
logging.getLogger("app").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        redirect_slashes=False,
    )

    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()


@app.exception_handler(AppError)
async def app_exception_handler(_request: Request, exc: AppError):
    logger.warning(f"{exc.code}: {exc.message}")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": str(exc),
            }
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}
