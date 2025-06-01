from fastapi import HTTPException
from jose import jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY")

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload  # Should contain "user_id"
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")