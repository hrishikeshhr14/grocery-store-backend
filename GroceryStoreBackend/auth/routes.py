from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Request
from GroceryStoreBackend.auth.dependencies import get_current_user
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import jwt, JWTError
from GroceryStoreBackend.database.db import get_connection
load_dotenv() 
import os
import datetime
from typing import List
from dotenv import load_dotenv

load_dotenv() 

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set. Check your .env file and dotenv loading.")

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
            "user_id": str(user[0]),  # <-- Convert UUID to string!
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        return {
            "token": token,
            "user": {
                "name": user[1],
                "email": user[2]
            }
        }
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

class OrderItem(BaseModel):
    item_name: str
    quantity: int
    price: int
    discount: float = 0.0
    tax: float = 0.0

class OrderCreate(BaseModel):
    customer_name: str
    payment_method: str = "Cash"
    discount: float = 0.0
    items: List[OrderItem]

@router.post("/orders")
def create_order(order: OrderCreate, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()

    try:
        # Insert into orders with user_id, payment_method, discount
        cur.execute(
            "INSERT INTO orders (customer_name, user_id, payment_method, discount) VALUES (%s, %s, %s, %s) RETURNING id",
            (order.customer_name, user["user_id"], order.payment_method, order.discount)
        )
        order_id = cur.fetchone()[0]

        # Insert order items with discount and tax
        for item in order.items:
            cur.execute(
                "INSERT INTO order_items (order_id, item_name, quantity, price, discount, tax) VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, item.item_name, item.quantity, item.price, item.discount, item.tax)
            )

        conn.commit()
        return {"message": "Order created successfully", "order_id": order_id}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
        
#GET
@router.get("/orders")
def list_orders(user=Depends(get_current_user)):
    print("User:", user)  # Debug: See what user is
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, customer_name, created_at, payment_method, discount FROM orders WHERE user_id = %s", (user["user_id"],))
        orders = cur.fetchall()
        print("Orders fetched:", orders)  # Debug

        order_list = []
        for order in orders:
            cur.execute(
                "SELECT item_name, quantity, price, discount, tax FROM order_items WHERE order_id = %s",
                (order[0],)
            )
            items = cur.fetchall()
            print("Items for order", order[0], ":", items)  # Debug
            total = sum((item[1] * item[2]) - item[1] * item[3] + item[1] * item[4] for item in items)
            order_list.append({
                "order_id": order[0],
                "customer_name": order[1],
                "created_at": str(order[2]),
                "payment_method": order[3],
                "order_discount": float(order[4]),
                "total": total,
                "items": [
                    {
                        "item_name": item[0],
                        "quantity": item[1],
                        "price": item[2],
                        "discount": item[3],
                        "tax": item[4]
                    }
                    for item in items
                ]
            })

        return {"orders": order_list}
    except Exception as e:
        print("Error in /orders:", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@router.get("/products")
def get_products(user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, category, price, stock, created_at FROM products WHERE user_id = %s ORDER BY created_at DESC", (user["user_id"],))
        rows = cur.fetchall()
        products = [
            {
                "id": str(row[0]),
                "name": row[1],
                "category": row[2],
                "price": float(row[3]),
                "stock": row[4],
                "created_at": row[5].isoformat()
            }
            for row in rows
        ]
        return {"products": products}
    finally:
        cur.close()
        conn.close()

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float
    stock: int

class ProductUpdate(BaseModel):
    name: str = None
    category: str = None
    price: float = None
    stock: int = None

@router.post("/products")
def add_product(product: ProductCreate, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO products (name, category, price, stock, user_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (product.name, product.category, product.price, product.stock, user["user_id"])
        )
        product_id = cur.fetchone()[0]
        conn.commit()
        return {"message": "Product added", "id": product_id}
    finally:
        cur.close()
        conn.close()

@router.put("/products/{product_id}")
def update_product(product_id: int, product: ProductUpdate, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        fields = []
        values = []
        for field, value in product.dict(exclude_unset=True).items():
            fields.append(f"{field} = %s")
            values.append(value)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        values.append(user["user_id"])
        values.append(product_id)
        query = f"UPDATE products SET {', '.join(fields)} WHERE user_id = %s AND id = %s"
        cur.execute(query, tuple(values))
        conn.commit()
        return {"message": "Product updated"}
    finally:
        cur.close()
        conn.close()

@router.delete("/products/{product_id}")
def delete_product(product_id: int, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM products WHERE user_id = %s AND id = %s", (user["user_id"], product_id))
        conn.commit()
        return {"message": "Product deleted"}
    finally:
        cur.close()
        conn.close()