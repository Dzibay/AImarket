import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_bot(x_bot_token: str = Header(default="")) -> None:
    expected = settings.bot_internal_token
    if not expected or not x_bot_token:
        raise HTTPException(status_code=401, detail="unauthorized")
    if not secrets.compare_digest(x_bot_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="unauthorized")
