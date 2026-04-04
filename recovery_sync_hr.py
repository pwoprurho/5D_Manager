import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from backend.app.database import supabase

def sync_hr_user():
    email = "hr@vinicius.int"
    print(f"Checking for existing Auth user: {email}")
    
    auth_users = supabase.auth.admin.list_users()
    target_user = None
    
    for user in auth_users:
        if user.email == email:
            target_user = user
            break
            
    if not target_user:
        print("Error: HR user not found in Auth. Please run setup_dev_accounts.py if it's completely missing.")
        return

    user_id = target_user.id
    print(f"Found Auth User ID: {user_id}")
    
    # Check if record exists in public.user
    res = supabase.table("user").select("*").eq("id", user_id).execute()
    if res.data:
        print(f"Public profile already exists: {res.data[0]}")
        if res.data[0]["role"] != "admin":
            print("Updating role to admin...")
            supabase.table("user").update({"role": "admin"}).eq("id", user_id).execute()
            print("Done!")
    else:
        print("Inserting missing public profile...")
        supabase.table("user").insert({
            "id": user_id,
            "email": email,
            "username": "hr",
            "role": "admin",
            "is_active": True
        }).execute()
        print("Successfully synced HR admin profile.")

if __name__ == "__main__":
    sync_hr_user()
