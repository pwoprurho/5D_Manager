import os
import sys

# Ensure we can find the backend app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.app.database import supabase

def register_engineer3():
    print("🚀 PROVISIONING ENGINEER 3 PROTOCOL...")
    
    eng3 = {
        "email": "engineer3@vinicius.int",
        "password": "Vinicius2026",
        "username": "mechanical_engineer",
        "role": "engineer"
    }

    try:
        # Check if exists
        existing = supabase.table("user").select("id").eq("username", eng3["username"]).execute()
        if existing.data:
            print("⚠️ User already exists in public table. Skipping creation.")
            return

        print(f"Creating Auth User: {eng3['username']}")
        auth_response = supabase.auth.admin.create_user({
            "email": eng3["email"],
            "password": eng3["password"],
            "email_confirm": True,
            "user_metadata": {
                "username": eng3["username"],
                "role": eng3["role"]
            }
        })
        
        user_id = auth_response.user.id
        print(f"✅ Auth User created with ID: {user_id}")
        
        print(f"Synchronizing to public metadata table...")
        user_data = {
            "id": user_id,
            "username": eng3["username"],
            "email": eng3["email"],
            "role": eng3["role"],
            "is_active": True
        }
        res = supabase.table('user').upsert(user_data).execute()
        if hasattr(res, 'data') and res.data:
            print(f"✅ User synced.")
        else:
            print(f"⚠️ Table sync response: {res}")
            
    except Exception as e:
        print(f"❌ FAILED to create user {eng3['username']}: {str(e)}")

if __name__ == "__main__":
    register_engineer3()
