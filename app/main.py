import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.repositories.database import init_db
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.health import router as health_router
from app.routers.logs import router as logs_router
from app.routers.problems import router as problems_router
from app.routers.submissions import router as submissions_router
from app.routers.users import router as users_router
from app.routers.web import router as web_router
from app.services.auth_service import ensure_initial_admin
from app.utils.exception_handlers import register_exception_handlers


# configure standard application logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# resolve the static directory
BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "frontend" / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    prepare persistent resources on startup
    """

    # create the database schema
    init_db()

    # create the initial administrator when required
    admin = ensure_initial_admin()

    logger.info(
        "initial administrator available as %s",
        admin["username"],
    )

    yield


# create the fastapi application
app = FastAPI(
    title="Mini Online Judge",
    lifespan=lifespan,
)

# register shared exception handlers
register_exception_handlers(app)

# use an environment variable or the default local secret
session_secret = os.getenv(
    "SESSION_SECRET",
    "development-only-change-this-secret",
)

# configure signed session cookies
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="oj_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)

# expose css and javascript files
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

# connect api and html routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(submissions_router)
app.include_router(users_router)
app.include_router(logs_router)
app.include_router(admin_router)
app.include_router(web_router)