from supabase import create_client, Client
from ..config import settings

from ..database import supabase
from ..config import settings

def get_supabase_client() -> Client:
    """Return the global Supabase client singleton."""
    return supabase

def upload_photo(file_bytes: bytes, filename: str, project_id: int, wp_id: int) -> str:
    """Upload a photo to Supabase Storage and return the public URL."""
    import time
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    timestamp = int(time.time())
    path = f"projects/{project_id}/wp_{wp_id}/{timestamp}_{filename}"
    
    try:
        print(f"Uploading photo to bucket: {bucket}, path: {path}")
        # Removed 'upsert' as it causes TypeError in this environment/library version
        client.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": "image/jpeg"}
        )
        
        result = client.storage.from_(bucket).get_public_url(path)
        print(f"Upload successful. URL: {result}")
        return result
    except Exception as upload_err:
        print(f"Supabase Storage Error: {str(upload_err)}")
        raise upload_err

def upload_file(file_bytes: bytes, filename: str, path_prefix: str) -> str:
    """Upload a generic file (e.g. .ifc) to Supabase Storage and return the public URL."""
    import time
    client = get_supabase_client()
    bucket = settings.SUPABASE_STORAGE_BUCKET
    timestamp = int(time.time())
    path = f"{path_prefix}/{timestamp}_{filename}"
    
    try:
        print(f"Uploading file to bucket: {bucket}, path: {path}")
        client.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": "application/octet-stream"}
        )
        
        result = client.storage.from_(bucket).get_public_url(path)
        print(f"Upload successful. URL: {result}")
        return result
    except Exception as upload_err:
        print(f"Supabase Storage Error: {str(upload_err)}")
        raise upload_err

def get_photo_url(path: str) -> str:
    """Get the public URL for a stored photo."""
    client = get_supabase_client()
    return client.storage.from_(settings.SUPABASE_STORAGE_BUCKET).get_public_url(path)
