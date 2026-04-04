import sys
import os

# Ensure we can import from the current directory (app)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.database import Session, engine
    from app.models import User, UserRole
    from app.auth import get_password_hash
except ImportError as e:
    print(f"Error: Could not import application modules. {e}")
    print("Make sure you are running this from the 'backend' directory.")
    sys.exit(1)

def create_user(username, email, password, role_str="staff"):
    # Convert role string to Enum
    try:
        role = UserRole(role_str)
    except ValueError:
        print(f"Error: Invalid role '{role_str}'. Valid roles are: staff, manager, director, admin")
        return

    try:
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
    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_user.py <username> <email> <password> [role]")
        print("Default role is 'staff'.")
        sys.exit(1)

    uname = sys.argv[2] if sys.argv[1] == "scripts/create_user.py" else sys.argv[1] # Handle accidental double path
    # Actually, simpler:
    args = [a for a in sys.argv if not a.endswith(".py")]
    if len(args) < 3:
         print("Usage: python create_user.py <username> <email> <password> [role]")
         sys.exit(1)
         
    create_user(args[0], args[1], args[2], args[3] if len(args) > 3 else "staff")
