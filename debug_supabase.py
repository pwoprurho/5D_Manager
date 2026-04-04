import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.database import supabase

def debug_tables():
    print("Checking connection...")
    try:
        # Try a simple select from a known working table
        res = supabase.table("user").select("count", count="exact").limit(1).execute()
        print("User table connection: OK")
        
        # Check design table
        print("\nChecking 'design' table...")
        try:
            res_design = supabase.table("design").select("*").limit(1).execute()
            print("Design table access: OK")
            print("Data:", res_design.data)
        except Exception as e:
            print(f"Design table access: FAILED - {e}")

        # Raw RPC check or similar if possible, but let's try to query the schema info if postgres allows
        print("\nAttempting to query information_schema via RPC (if enabled)...")
        try:
            # This requires a custom function usually, let's try a direct query on a system table if exposed
            # but usually they are not.
            pass
        except:
            pass

    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    debug_tables()
