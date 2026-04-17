import re
import os

files_to_check = [
    "c:\\Users\\Administrator\\outbound-caller-python\\backend\\app\\main.py",
    "c:\\Users\\Administrator\\outbound-caller-python\\templates\\admin_users.html",
    "c:\\Users\\Administrator\\outbound-caller-python\\templates\\register.html"
]

for fp in files_to_check:
    with open(fp, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple replaces for Python occurrences of staff -> engineer
    if fp.endswith(".py"):
        content = content.replace('"role": "staff"', '"role": "engineer"')
        content = content.replace("'role': 'staff'", "'role': 'engineer'")
        content = content.replace('models.UserRole.staff', 'models.UserRole.engineer')
        content = content.replace("Staff and managers", "Engineers and managers")
        # Ensure we cover user=Depends...staff
        content = content.replace('role: str = Form("staff")', 'role: str = Form("engineer")')
        content = content.replace('role: models.UserRole = models.UserRole.staff', 'role: models.UserRole = models.UserRole.engineer')
        
    elif fp.endswith(".html"):
        content = content.replace('role === "staff"', 'role === "engineer"')
        content = content.replace("role === 'staff'", "role === 'engineer'")
        content = content.replace('value="staff"', 'value="engineer"')
        content = content.replace("FIELD_STAFF", "SITE_ENGINEER")
        content = content.replace("staff: ", "engineer: ")
        
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)

print("Roles modified!")
