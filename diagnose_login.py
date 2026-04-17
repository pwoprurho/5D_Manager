"""Diagnose the exact login issue."""
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
from backend.app.database import supabase

print("=" * 50)
print("DIAGNOSTIC: Login Credentials Test")
print("=" * 50)

# Step 1: Check public.user table
print("\n--- PUBLIC.USER TABLE ---")
try:
    result = supabase.table("user").select("id, username, email, role").execute()
    if result.data:
        for u in result.data:
            print(f"  {u['username']} | {u['email']} | {u['role']} | ID: {u['id']}")
    else:
        print("  ❌ TABLE IS EMPTY!")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Step 2: Check Supabase Auth users
print("\n--- SUPABASE AUTH USERS ---")
try:
    resp = supabase.auth.admin.list_users()
    auth_users = resp.users if hasattr(resp, 'users') else (resp if isinstance(resp, list) else [])
    for au in auth_users:
        print(f"  {au.email} | ID: {au.id} | confirmed: {au.email_confirmed_at is not None}")
except Exception as e:
    print(f"  ❌ Error listing auth users: {e}")

# Step 3: Try to sign in with BabaD credentials
print("\n--- SIGNIN TEST: BabaD@vinicius.int / Vinicius2026 ---")
try:
    auth_res = supabase.auth.sign_in_with_password({
        "email": "BabaD@vinicius.int",
        "password": "Vinicius2026"
    })
    if auth_res and auth_res.user:
        print(f"  ✅ SUCCESS! User ID: {auth_res.user.id}")
    else:
        print(f"  ❌ No user returned")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Step 4: Try the OLD password too
print("\n--- SIGNIN TEST: BabaD@vinicius.int / Vinicuis2026 (old typo) ---")
try:
    auth_res = supabase.auth.sign_in_with_password({
        "email": "BabaD@vinicius.int",
        "password": "Vinicuis2026"
    })
    if auth_res and auth_res.user:
        print(f"  ✅ OLD PASSWORD WORKS! User ID: {auth_res.user.id}")
    else:
        print(f"  ❌ No user returned")
except Exception as e:
    print(f"  ❌ FAILED: {e}")

# Step 5: Compare IDs
print("\n--- ID MISMATCH CHECK ---")
try:
    pub_result = supabase.table("user").select("id, email").execute()
    auth_resp = supabase.auth.admin.list_users()
    auth_users = auth_resp.users if hasattr(auth_resp, 'users') else []
    
    pub_map = {u["email"].lower(): u["id"] for u in (pub_result.data or [])}
    auth_map = {au.email.lower(): au.id for au in auth_users}
    
    all_emails = set(list(pub_map.keys()) + list(auth_map.keys()))
    for email in sorted(all_emails):
        pub_id = pub_map.get(email, "MISSING")
        auth_id = auth_map.get(email, "MISSING")
        match = "✅" if pub_id == auth_id else "❌ MISMATCH"
        print(f"  {email}: pub={pub_id[:12] if pub_id != 'MISSING' else pub_id}... auth={auth_id[:12] if auth_id != 'MISSING' else auth_id}... {match}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 50)
