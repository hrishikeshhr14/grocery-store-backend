from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from database.db import get_connection
import os
import datetime

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET")

class SignupSchema(BaseModel):
    name: str
    email: str
    password: str

class SigninSchema(BaseModel):
    email: str
    password: str

@router.post("/signup")
def signup(data: SignupSchema):
    hashed = pwd_context.hash(data.password)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                    (data.name, data.email, hashed))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/signin")
def signin(data: SigninSchema):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, password FROM users WHERE email = %s", (data.email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if not user or not pwd_context.verify(data.password, user[3]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        payload = {
            "user_id": user[0],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return {"token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
def me(request: Request):
    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Missing token")

    try:
        token = token.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["user_id"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            return {"user": {"id": user[0], "name": user[1], "email": user[2]}}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")