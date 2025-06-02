import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_URL = os.getenv("DB_URL")


def get_connection():
    return psycopg2.connect(DB_URL)