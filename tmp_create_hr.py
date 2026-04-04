import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import supabase

def create_hr_user():
    try:
        print("Signing up user hr@vinicius.int...")
        res = supabase.auth.sign_up({
            "email": "hr@vinicius.int",
            "password": "admin123"
        })
        
        user_id = res.user.id
        print(f"User created with ID: {user_id}")
        
        print("Updating role to admin...")
        # Since the trigger inserts 'staff', we just update it
        update_res = supabase.table("user").update({"role": "admin"}).eq("id", user_id).execute()
        print(f"Update response: {update_res.data}")
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_hr_user()
