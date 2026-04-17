import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

if url and key:
    supabase = create_client(url, key)
    try:
        # Update user roles
        res = supabase.table("user").update({"role": "engineer"}).eq("role", "staff").execute()
        print(f"Updated user roles: {res}")
        
        # We can also update projectassignment table 'assigned_role' if they had staff there
        res2 = supabase.table("projectassignment").update({"assigned_role": "engineer"}).eq("assigned_role", "staff").execute()
        print(f"Updated project assignments: {res2}")
        
    except Exception as e:
        print(f"Failed to update db roles: {e}")
else:
    print("No supabase credentials!")
