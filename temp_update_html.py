import os
import re

TEMPLATES_DIR = r"c:\Users\Administrator\outbound-caller-python\templates"

for filename in os.listdir(TEMPLATES_DIR):
    if filename.endswith(".html"):
        filepath = os.path.join(TEMPLATES_DIR, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Update manager to include director where appropriate
        # but the request says: "directors are also capable of adding BIM models or they have access to manager level roles"
        # Most of the JS usually says `['admin','manager','director']` already. Let's find any that don't have director.
        def repl_manager(match):
            arr = match.group(0)
            if 'manager' in arr and 'director' not in arr:
                return arr.replace("'manager'", "'manager','director'")
            return arr
            
        # Add president anywhere admin is present except if it's explicitly tied to a "Delete" or overriding button.
        # This is trickier in HTML. Let's look for ['admin', ...] arrays.
        def repl_admin(match):
            arr = match.group(0)
            if 'admin' in arr and 'president' not in arr:
                return arr.replace("'admin'", "'admin','president'")
            return arr

        # Identify javascript array includes e.g. `['admin', 'manager'].includes`
        new_content = re.sub(r"\[.*?\](?=\.includes)", repl_manager, content)
        new_content = re.sub(r"\[.*?\](?=\.includes)", repl_admin, new_content)
        
        # In admin_users.html there's an option for admin
        if filename == "admin_users.html":
            if '<option value="president">PRESIDENT</option>' not in new_content:
                new_content = new_content.replace(
                    '<option value="admin">GLOBAL_ADMIN</option>', 
                    '<option value="admin">GLOBAL_ADMIN</option>\n<option value="president">PRESIDENT</option>'
                )

        if new_content != content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
