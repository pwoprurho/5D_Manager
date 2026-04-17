import os
import shutil

# Target directory
target_dir = r"c:\Users\Administrator\outbound-caller-python\static\assets\training"
os.makedirs(target_dir, exist_ok=True)

# Source files (from artifacts)
source_base = r"C:\Users\Administrator\.gemini\antigravity\brain\e64b2770-6776-4318-bc6b-555228f66c94"

files_to_copy = {
    "analytics_dashboard_light_mode_1776192527095.png": "analytics_hud.png",
    ".system_generated/click_feedback/click_feedback_1776191831808.png": "kanban_board.png",
    ".system_generated/click_feedback/click_feedback_1776191910469.png": "site_manager.png",
    ".system_generated/click_feedback/click_feedback_1776191570525.png": "login_interface.png",
    ".system_generated/click_feedback/click_feedback_1776171664637.png": "user_registry.png",
    ".system_generated/click_feedback/click_feedback_1776172676595.png": "project_init.png"
}

for src_rel, dest_name in files_to_copy.items():
    src_path = os.path.join(source_base, src_rel)
    dest_path = os.path.join(target_dir, dest_name)
    if os.path.exists(src_path):
        shutil.copy2(src_path, dest_path)
        print(f"Copied: {src_rel} -> {dest_name}")
    else:
        print(f"Missing: {src_path}")
