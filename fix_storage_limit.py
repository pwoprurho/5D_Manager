from backend.app.database import supabase
from backend.app.config import settings

def update_storage_limit():
    bucket_id = settings.SUPABASE_STORAGE_BUCKET
    print(f"Targeting bucket: {bucket_id}")
    
    try:
        # Get current bucket info
        bucket = supabase.storage.get_bucket(bucket_id)
        current_limit = bucket.file_size_limit
        print(f"Current file size limit: {current_limit} bytes (~{current_limit/(1024*1024):.2f} MB)")
        
        # Default often is 50MB (52428800 bytes). User wants 50MB "extra".
        # Let's set it to at least 150MB to be safe, or just add 50MB.
        new_limit = (current_limit or 52428800) + (50 * 1024 * 1024)
        print(f"Proposed new limit: {new_limit} bytes (~{new_limit/(1024*1024):.2f} MB)")
        
        # Update bucket
        res = supabase.storage.update_bucket(
            bucket_id,
            options={
                "file_size_limit": new_limit,
                "public": True
            }
        )
        print("Successfully updated storage limit.")
        
        # Verify
        updated = supabase.storage.get_bucket(bucket_id)
        print(f"Verified new limit: {updated.file_size_limit} bytes")
        
    except Exception as e:
        print(f"Error updating bucket: {e}")

if __name__ == "__main__":
    update_storage_limit()
