from fastapi import Depends, HTTPException, Request
from jose import jwt, JWTError
from dotenv import load_dotenv  # ✅ Add this
import os

load_dotenv()  # ✅ Load variables from .env

JWT_SECRET = os.getenv("JWT_SECRET")

def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {"user_id": payload["user_id"]}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def create_access_token(user):
    payload = {
        "user_id": str(user.id),  # Ensure this is the UUID as a string
        # ...other fields...
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return token