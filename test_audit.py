import os
from supabase import create_client
from datetime import datetime

url = "https://dnyyznmitlchkqanbpem.supabase.co"
key = os.environ.get("SUPABASE_SERVICE_KEY")
if not key:
    with open(".env", "r") as f:
        for line in f:
            if "SUPABASE_SERVICE_KEY" in line:
                key = line.split("=")[1].strip().strip('"')

supabase = create_client(url, key)

try:
    res = supabase.table("audit_log").insert({
        "actor_id": "00000000-0000-0000-0000-000000000000",
        "target_id": "00000000-0000-0000-0000-000000000000",
        "action": "system_init",
        "details": {"message": "Audit Log Integrity Check"}
    }).execute()
    print("SUCCESS: audit_log table is reachable and active.")
except Exception as e:
    print(f"ERROR: audit_log table may be missing or inaccessible. Details: {e}")
