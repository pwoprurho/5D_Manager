import re
import os

MAIN_PY = r"c:\Users\Administrator\outbound-caller-python\backend\app\main.py"

with open(MAIN_PY, "r", encoding="utf-8") as f:
    content = f.read()

def replacer(match):
    # match.group(1) is the list of roles e.g. "models.UserRole.admin, models.UserRole.director"
    roles_str = match.group(1)
    # determine roles as a set
    roles = set(r.strip() for r in roles_str.split(","))
    
    if "models.UserRole.manager" in roles:
        roles.add("models.UserRole.director")
    
    if "models.UserRole.admin" in roles:
        # Check if it's a manual override.
        # we can look backwards to find the function definition 
        # But a safer heuristic is to look at the surrounding 200 characters
        context = content[max(0, match.start() - 250):match.end()]
        if not ("def delete" in context or "def update_material_request_status" in context):
            roles.add("models.UserRole.president")
            
    # Also president needs to have access to User management implicitly as it's an admin privilege (non-manual override)
    # The endpoints /api/v1/users/ are admin endpoints
            
    # sort them nicely or just join
    # list to make deterministic
    sorted_roles = sorted(list(roles))
    return f"Depends(auth.check_role([{', '.join(sorted_roles)}]))"

new_content = re.sub(r'Depends\(auth\.check_role\(\[(.*?)\]\)\)', replacer, content)

with open(MAIN_PY, "w", encoding="utf-8") as f:
    f.write(new_content)
