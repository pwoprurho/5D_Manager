import os
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ["DATABASE_URL"]

# Fix the hardcoded @ password component from 'postgres.dnyyznmitlchkqanbpem:@kp0j0t0r_2026'
db_url = db_url.replace("@kp0j0t0r", quote_plus("@kp0j0t0r"))

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    # 1. Security & Lockout enhancements
    cur.execute("ALTER TABLE public.user ADD COLUMN IF NOT EXISTS security_question TEXT;")
    cur.execute("ALTER TABLE public.user ADD COLUMN IF NOT EXISTS security_answer TEXT;")
    cur.execute("ALTER TABLE public.user ADD COLUMN IF NOT EXISTS is_locked BOOLEAN DEFAULT FALSE;")
    
    # 2. Stage/Phase Model Architecture
    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.stage (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES public.project(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'not_started',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # 3. Link WorkPackages to Stages
    cur.execute("ALTER TABLE public.workpackage ADD COLUMN IF NOT EXISTS stage_id INTEGER REFERENCES public.stage(id) ON DELETE SET NULL;")
    
    # 4. Cleanup/Refactor
    # Removing blueprint is handled via logic, but we keep DB clean
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database altered successfully")
except Exception as e:
    print(f"Error: {e}")
