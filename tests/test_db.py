import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
POOLER_URL = os.getenv("POOLER_URL")
try:
    conn = psycopg2.connect(POOLER_URL, sslmode='require')
    print("Conexión exitosa")
    conn.close()
except Exception as e:
    print(f"Error: {e}")