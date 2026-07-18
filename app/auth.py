import os

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "")

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verificar_api_key(api_key: str = Depends(_api_key_header)) -> str:
    if not API_KEY:
        return ""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida o no proporcionada",
        )
    return api_key
