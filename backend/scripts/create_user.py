import sys
import os

# Add the backend directory to sys.path to allow imports from app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Session, engine
from app.models import User, UserRole
from app.auth import get_password_hash

def create_user(username, email, password, role_str="staff"):
    # Convert role string to Enum
    try:
        role = UserRole(role_str)
    except ValueError:
        print(f"Error: Invalid role '{role_str}'. Valid roles are: staff, manager, director, admin")
        return

    with Session(engine) as session:
        # Check if user already exists
        existing = session.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing:
            print(f"Error: User with username '{username}' or email '{email}' already exists.")
            return

        new_user = User(
            username=username,
            email=email,
            hashed_password=get_password_hash(password),
            role=role
        )
        session.add(new_user)
        session.commit()
        print(f"Successfully created user '{username}' with role '{role.value}'.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_user.py <username> <email> <password> [role]")
        print("Default role is 'staff'.")
        sys.exit(1)

    uname = sys.argv[1]
    uemail = sys.argv[2]
    upass = sys.argv[3]
    urole = sys.argv[4] if len(sys.argv) > 4 else "staff"

    create_user(uname, uemail, upass, urole)
