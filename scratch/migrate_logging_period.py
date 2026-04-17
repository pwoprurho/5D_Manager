import os
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ["DATABASE_URL"]

# Fix the hardcoded @ password component
if "@kp0j0t0r" in db_url:
    db_url = db_url.replace("@kp0j0t0r", quote_plus("@kp0j0t0r"))

try:
    print("Connecting to DB...")
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    print("Adding logging_period to workpackage...")
    cur.execute("ALTER TABLE public.workpackage ADD COLUMN IF NOT EXISTS logging_period TEXT DEFAULT 'daily';")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database migration successful: workpackage.logging_period added.")
except Exception as e:
    print(f"Error during migration: {e}")
