import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


logger = logging.getLogger(__name__)


async def http_exception_handler(
    _request: Request,
    exception: StarletteHTTPException,
) -> JSONResponse:
    """
    convert fastapi http errors into the shared api structure
    """

    if isinstance(exception.detail, str):
        message = exception.detail
        data = None
    else:
        message = "request error"
        data = {"detail": exception.detail}

    return JSONResponse(
        status_code=exception.status_code,
        headers=exception.headers,
        content={
            "code": exception.status_code,
            "message": message,
            "data": data,
        },
    )


async def validation_exception_handler(
    _request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """
    convert pydantic request errors into the shared api structure
    """

    errors = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exception.errors()
    ]

    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "validation error",
            "data": {"errors": errors},
        },
    )


async def unhandled_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """
    log unexpected errors and hide internal details from clients
    """

    logger.exception(
        "unhandled error for %s %s",
        request.method,
        request.url.path,
        exc_info=exception,
    )

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "internal server error",
            "data": None,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    attach all shared error handlers to the fastapi application
    """

    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )
