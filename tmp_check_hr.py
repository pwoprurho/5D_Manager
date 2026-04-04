import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.database import supabase

def check_hr():
    res = supabase.table("user").select("*").eq("email", "hr@vinicius.int").execute()
    if res.data:
        print("Found user:", res.data)
        if res.data[0]["role"] != "admin":
            upd = supabase.table("user").update({"role": "admin"}).eq("email", "hr@vinicius.int").execute()
            print("Updated to admin:", upd.data)
    else:
        print("User not found in public.user table yet.")

if __name__ == "__main__":
    check_hr()
