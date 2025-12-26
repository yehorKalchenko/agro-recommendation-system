from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback
from pydantic import ValidationError as PydanticValidationError
from app.api.routes.diagnose import router as diagnose_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgroDiag",
    version="1.0.0",
    description="AI-Powered Agricultural Plant Disease Diagnostic System",
    contact={
        "name": "AgroDiag Support",
        "email": "support@agrodiag.example.com",
    },
    license_info={
        "name": "Proprietary",
    },
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTPExceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "Request failed", "detail": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    errors = exc.errors()
    detail = "; ".join([f"{e['loc'][-1]}: {e['msg']}" for e in errors])

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": detail}
    )


@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Handle Pydantic validation errors from manual model construction."""
    errors = exc.errors()
    detail = "; ".join([f"{e['loc'][-1] if e['loc'] else 'field'}: {e['msg']}" for e in errors])

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "Validation error", "detail": detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unhandled exceptions.
    Logs full traceback but returns generic error to client.
    """
    # Log full error details for debugging
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}",
        exc_info=True
    )

    # Return generic error to client (don't leak internal details)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please contact support if the issue persists."
        }
    )


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(diagnose_router, prefix="/v1")
