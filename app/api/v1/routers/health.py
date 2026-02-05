from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health")


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
