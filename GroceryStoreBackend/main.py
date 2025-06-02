from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from GroceryStoreBackend.auth.routes import router as auth_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "FastAPI backend connected!"}