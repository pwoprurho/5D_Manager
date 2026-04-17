"""Direct password reset for all seed users via admin API.
This bypasses the unreliable list_users/delete flow.
"""
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.database import supabase

PASSWORD = "Vinicius2026"

# Get all users from public.user table (which was successfully synced)
print("📋 Fetching users from public.user table...")
result = supabase.table("user").select("id, username, email, role").execute()

if not result.data:
    print("❌ No users found in public.user table!")
    sys.exit(1)

print(f"Found {len(result.data)} users:\n")

for user in result.data:
    uid = user["id"]
    email = user["email"]
    username = user["username"]
    print(f"🔄 Resetting password for {username} ({email})...")
    
    try:
        supabase.auth.admin.update_user_by_id(
            uid,
            {"password": PASSWORD}
        )
        print(f"   ✅ Password set to: {PASSWORD}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")

print(f"\n🏁 Done. All users should now have password: {PASSWORD}")
print("   Try signing in with: BabaD / Vinicius2026")
