import os
from urllib.parse import quote_plus
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ["DATABASE_URL"]
db_url = db_url.replace("@kp0j0t0r", quote_plus("@kp0j0t0r"))

def fix_enum():
    try:
        # Connect with autocommit for ALTER TYPE
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Checking user_role enum...")
        cur.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'user_role';")
        existing_roles = [r[0] for r in cur.fetchall()]
        print(f"Existing roles: {existing_roles}")
        
        if 'engineer' not in existing_roles:
            print("Adding 'engineer' to user_role enum...")
            cur.execute("ALTER TYPE user_role ADD VALUE 'engineer';")
            print("'engineer' added successfully.")
        else:
            print("'engineer' already exists in enum.")
            
        print("Updating legacy 'staff' accounts to 'engineer'...")
        cur.execute("UPDATE public.user SET role = 'engineer' WHERE role = 'staff';")
        print("Update complete.")
        
        cur.close()
        conn.close()
        print("\nSUCCESS: Database terminology synchronization complete.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_enum()
