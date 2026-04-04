import re
import os

MAIN_PY = r"c:\Users\Administrator\outbound-caller-python\backend\app\main.py"

with open(MAIN_PY, "r", encoding="utf-8") as f:
    content = f.read()

def replacer(match):
    roles_str = match.group(1)
    roles = set(r.strip() for r in roles_str.split(","))
    
    # We want president to have all admin backend capabilities without exception.
    if "models.UserRole.admin" in roles:
        roles.add("models.UserRole.president")
            
    sorted_roles = sorted(list(roles))
    return f"Depends(auth.check_role([{', '.join(sorted_roles)}]))"

new_content = re.sub(r'Depends\(auth\.check_role\(\[(.*?)\]\)\)', replacer, content)

with open(MAIN_PY, "w", encoding="utf-8") as f:
    f.write(new_content)
