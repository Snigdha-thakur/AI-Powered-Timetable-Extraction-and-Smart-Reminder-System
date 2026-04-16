from fastapi import Depends, HTTPException, Header
from app.utils.jwt_handler import decode_token


def get_current_user(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must be in the format: Bearer <token>")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return payload["sub"]
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
