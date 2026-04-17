import time
import mimetypes
from ..database import supabase
from ..config import settings


def get_supabase_client():
    """Return the global Supabase client singleton."""
    return supabase


def upload_photo(file_bytes: bytes, filename: str, project_id: int, wp_id: int) -> str:
    """Upload a site photo/video to Supabase Storage and return the public URL."""
    bucket = settings.SUPABASE_STORAGE_BUCKET
    timestamp = int(time.time())
    path = f"projects/{project_id}/wp_{wp_id}/{timestamp}_{filename}"
    
    # Resolve mime type dynamically
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "image/jpeg" # Fallback for telemetry captures
    
    try:
        supabase.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": mime_type}
        )
        return supabase.storage.from_(bucket).get_public_url(path)
    except Exception as upload_err:
        raise upload_err


def upload_file(file_bytes: bytes, filename: str, path_prefix: str) -> str:
    """Upload a generic infrastructure resource (PDF/CAD) and return the public URL."""
    bucket = settings.SUPABASE_STORAGE_BUCKET
    timestamp = int(time.time())
    path = f"{path_prefix}/{timestamp}_{filename}"
    
    # Resolve mime type dynamically for blueprints and documentation
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    try:
        supabase.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": mime_type}
        )
        return supabase.storage.from_(bucket).get_public_url(path)
    except Exception as upload_err:
        raise upload_err
