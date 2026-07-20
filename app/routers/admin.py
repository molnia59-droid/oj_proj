from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.dependencies.auth import require_roles
from app.services.backup_service import (
    create_backup,
    get_backup_list,
    restore_backup,
)


router = APIRouter(
    prefix="/api/admin/backups",
    tags=["backups"],
)


@router.post("", status_code=201)
async def create_backup_endpoint(
    current_user: dict = Depends(require_roles("admin")),
):
    """
    create a database backup for an administrator
    """

    try:
        data = create_backup(current_user)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "backup creation failed",
                "data": None,
            },
        )

    return {
        "code": 201,
        "message": "backup created",
        "data": data,
    }


@router.get("")
async def get_backups_endpoint(
    _current_user: dict = Depends(require_roles("admin")),
):
    """
    return all available backup metadata
    """

    return {
        "code": 200,
        "message": "ok",
        "data": get_backup_list(),
    }


@router.post("/{backup_id}/restore")
async def restore_backup_endpoint(
    backup_id: str,
    current_user: dict = Depends(require_roles("admin")),
):
    """
    validate and restore one selected database backup
    """

    try:
        data = restore_backup(
            backup_id,
            current_user,
        )
    except LookupError as error:
        return JSONResponse(
            status_code=404,
            content={
                "code": 404,
                "message": str(error),
                "data": None,
            },
        )
    except ValueError as error:
        return JSONResponse(
            status_code=400,
            content={
                "code": 400,
                "message": str(error),
                "data": None,
            },
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "backup restore failed",
                "data": None,
            },
        )

    return {
        "code": 200,
        "message": "backup restored",
        "data": data,
    }
