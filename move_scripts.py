import os
import shutil
import glob

def clean_repo():
    root = os.getcwd()
    archive_dir = os.path.join(root, "scripts", "archive")
    
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
        print(f"Created {archive_dir}")

    # Patterns to move
    patterns = ["temp_*", "tmp_*", "fix_*", "alter_db.py", "debug_supabase.py", "diagnose_login.py", "test_*.py", "verify_*.py", "inspect_data.py"]
    
    files_to_move = []
    for pattern in patterns:
        files_to_move.extend(glob.glob(os.path.join(root, pattern)))

    moved_count = 0
    for file_path in files_to_move:
        if os.path.isfile(file_path):
            file_name = os.path.basename(file_path)
            # Don't move the script itself
            if file_name == "move_scripts.py":
                continue
            
            dest = os.path.join(archive_dir, file_name)
            try:
                shutil.move(file_path, dest)
                print(f"Moved: {file_name} -> scripts/archive/")
                moved_count += 1
            except Exception as e:
                print(f"Error moving {file_name}: {e}")

    print(f"\nCleanup finished. Moved {moved_count} scripts.")

if __name__ == "__main__":
    clean_repo()
