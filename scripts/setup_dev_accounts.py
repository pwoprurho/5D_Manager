import os
import sys
import argparse
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import supabase
from backend.app.models import UserRole

def setup_dev_user(email, password, username, role=UserRole.admin):
    print(f"--- Creating Dev User: {username} ({email}) ---")
    
    try:
        # 1. Create user in Supabase Auth (admin client)
        auth_res = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"username": username}
        })
        
        user_id = auth_res.user.id
        print(f"Success: Auth User created/found: {user_id}")
        
        # 2. Update the role in public.user 
        # (The DB trigger `handle_new_user` will have already inserted a row with default role 'staff')
        db_res = supabase.table("user").update({
            "role": role.value,
            "username": username
        }).eq("id", user_id).execute()
        
        print(f"Success: Public Profile Updated to role: {role.value}")
        print(f"\nSUCCESS! You can now login with:")
        print(f"Email: {email}")
        print(f"Password: {password}")
            
    except Exception as e:
        print(f"Exception during setup: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--role", default="admin")
    args = parser.parse_args()
    
    setup_dev_user(args.email, args.password, args.username, UserRole(args.role))
