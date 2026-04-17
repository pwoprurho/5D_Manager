import os
import sys
sys.path.append(os.getcwd())
from backend.app.database import supabase
from backend.app.config import settings

def reset_storage():
    print("--- 5D Mission Control: Storage Reset Sequence Initiated ---")
    
    buckets_to_reset = ["site-photos", "designs"]
    
    for b_id in buckets_to_reset:
        print(f"\n[SCANNING] Targets identified for bucket: {b_id}")
        
        # 1. Attempt Deletion (Full Wipe)
        try:
            # We must empty the bucket first before deleting it in some versions
            print(f"[RECLAMATION] Emptying bucket: {b_id}...")
            files = supabase.storage.from_(b_id).list()
            if files:
                file_names = [f['name'] for f in files]
                supabase.storage.from_(b_id).remove(file_names)
            
            print(f"[PURGING] Deleting bucket: {b_id}...")
            supabase.storage.delete_bucket(b_id)
            print(f"[SUCCESS] {b_id} has been purged from orbit.")
        except Exception as e:
            print(f"[WARNING] Deletion failed or bucket not found: {e}")

        # 2. Re-Initialization
        try:
            print(f"[PROVISIONING] Recreating bucket: {b_id}...")
            # We attempt to create it with public access and high capacity
            # Note: file_size_limit might still be capped by Supabase plan
            res = supabase.storage.create_bucket(
                b_id, 
                options={
                    "public": True,
                    "file_size_limit": 104857600, # 100MB
                    "allowed_mime_types": ["*/*"]
                }
            )
            print(f"[READY] {b_id} is now online and operational.")
        except Exception as e:
            print(f"[CRITICAL] Recreation failure for {b_id}: {e}")

    print("\n--- Storage Reset Cycle Complete ---")

if __name__ == "__main__":
    reset_storage()
