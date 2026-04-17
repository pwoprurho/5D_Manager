import os
import sys
import io
import time
from pypdf import PdfReader, PdfWriter
try:
    from PIL import Image
    HAS_PILLOW = True
except:
    HAS_PILLOW = False

sys.path.append(os.getcwd())
from backend.app.database import supabase
from backend.app.config import settings

def manual_ingest(file_path):
    print(f"--- 5D Mission Control: Manual Ingest Sequence ---")
    print(f"[TARGET] {file_path}")
    
    if not os.path.exists(file_path):
        print("[ERROR] File not found.")
        return

    file_size = os.path.getsize(file_path)
    print(f"[STATUS] Current Size: {file_size/1024/1024:.1f}MB")
    
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 1. OPTIMIZATION
    if file_path.lower().endswith('.pdf') and file_size > 50 * 1024 * 1024:
        print("[OPTIMIZING] Triggering aggressive stream compression...")
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            writer = PdfWriter()
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
            writer.remove_unreferenced_objects()
            writer.add_metadata(reader.metadata)
            
            out = io.BytesIO()
            writer.write(out)
            file_bytes = out.getvalue()
            new_size = len(file_bytes)
            print(f"[SUCCESS] Optimization complete: {new_size/1024/1024:.1f}MB")
        except Exception as e:
            print(f"[WARNING] Optimization failed: {e}")

    # 2. UPLOAD
    bucket = "site-photos"
    timestamp = int(time.time())
    dest_path = f"project-resources/{timestamp}_zaria.pdf"
    
    print(f"[UPLOADING] Sending to cloud: {dest_path}")
    try:
        res = supabase.storage.from_(bucket).upload(
            path=dest_path,
            file=file_bytes,
            file_options={"content-type": "application/pdf"}
        )
        url = supabase.storage.from_(bucket).get_public_url(dest_path)
        print(f"\n[MISSION COMPLETE]")
        print(f"URL: {url}")
    except Exception as e:
        print(f"[CRITICAL] Upload failed: {e}")

if __name__ == "__main__":
    manual_ingest(r"C:\Users\Administrator\Downloads\zaria.pdf")
