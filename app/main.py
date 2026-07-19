import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.repositories.database import init_db
from app.repositories.user_repository import clear_all_user_presence
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


# configure standard application logs for local development
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# resolve the static directory once when the module is imported
BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "frontend" / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    prepare persistent resources on startup and clear presence on shutdown
    """

    # create a new clean database schema when no database exists
    init_db()

    # every new server process starts with all users marked offline
    clear_all_user_presence()

    # ensure that a first administrator is available for a clean database
    admin = ensure_initial_admin()
    logger.info(
        "initial administrator available as %s",
        admin["username"],
    )

    yield

    # a graceful shutdown immediately marks every account offline
    clear_all_user_presence()


# create the central fastapi application
app = FastAPI(
    title="Mini Online Judge",
    lifespan=lifespan,
)

# convert validation and unhandled errors into the required response format
register_exception_handlers(app)

# sign session cookies with a configurable secret
session_secret = os.getenv(
    "SESSION_SECRET",
    "development-only-change-this-secret",
)

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="oj_session",
    same_site="lax",
    https_only=False,
)

# expose css and javascript files under the static url
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)

# connect every api and html router in one visible place
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(submissions_router)
app.include_router(users_router)
app.include_router(logs_router)
app.include_router(admin_router)
app.include_router(web_router)
