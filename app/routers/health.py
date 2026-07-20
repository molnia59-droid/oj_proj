from fastapi import APIRouter


router = APIRouter()


@router.get("/api/health")
async def health_check():
    """
    return a simple response used to confirm server availability
    """

    return {
        "code": 200,
        "message": "ok",
        "data": {"status": "running"},
    }
