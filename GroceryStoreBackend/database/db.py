import os
from dotenv import load_dotenv

from GroceryStoreBackend.database.db import get_connection

load_dotenv()

DB_URL = os.getenv("DB_URL")


def get_connection():
    return psycopg2.connect(DB_URL)