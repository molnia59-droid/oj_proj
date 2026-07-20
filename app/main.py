import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.repositories.database import init_db
from app.repositories.user_repository import clear_all_user_presence
from app.services.auth_service import ensure_initial_admin
from app.utils.exception_handlers import register_exception_handlers


# configure application logging
logging.basicConfig(
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
):
    """
    prepare the database when the application starts
    """

    # create all database tables if they do not exist
    init_db()

    # remove old online status values after a server restart
    clear_all_user_presence()

    # create the first administrator when the users table is empty
    admin = ensure_initial_admin()

    logger.info(
        "initial administrator is available as %s",
        admin["username"],
    )

    # allow fastapi to start processing requests
    yield

    # mark every user as offline during a normal shutdown
    clear_all_user_presence()


# create the central fastapi application
app = FastAPI(
    title="Mini Online Judge",
    version="0.3.0",
    lifespan=lifespan,
)


# register handlers for validation and unexpected errors
register_exception_handlers(
    app,
)


# read the cookie signing secret from an environment variable
session_secret = os.getenv(
    "SESSION_SECRET",
    "development-only-change-this-secret",
)


# add signed session cookie support
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="oj_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)


@app.get("/")
async def root():
    """
    show that the third project part is running
    """

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "project": "mini online judge",
            "part": 3,
            "status": "running",
        },
    }


@app.get("/api/health")
async def health_check():
    """
    return the current application status
    """

    return {
        "code": 200,
        "message": "ok",
        "data": {
            "status": "running",
            "part": 3,
        },
    }