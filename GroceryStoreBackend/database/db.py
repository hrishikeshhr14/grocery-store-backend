import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")

def get_connection():
    return psycopg2.connect(DB_URL)