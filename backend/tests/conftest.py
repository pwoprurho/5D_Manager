import pytest
from sqlmodel import Session, SQLModel, create_engine
from app.main import app
from app.database import get_session
from fastapi.testclient import TestClient

# Use separate SQLite for testing
sqlite_url = "sqlite:///./test_api.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # Seed test users
        from app.models import User, UserRole
        from app.auth import get_password_hash
        admin_user = User(
            username="admin", 
            email="admin_test@5d.com", 
            hashed_password=get_password_hash("admin123"), 
            role=UserRole.admin
        )
        session.add(admin_user)
        session.commit()
        
        yield session
    SQLModel.metadata.drop_all(engine)

@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
