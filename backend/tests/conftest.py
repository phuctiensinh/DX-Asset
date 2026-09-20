import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal, Base, engine
from app.core.security import create_access_token
from app.models import User, UserRole

@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def db() -> Session:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    # Check if admin user exists, if not seed database
    admin = session.query(User).filter(User.role == UserRole.ADMIN).first()
    if not admin:
        import sys, os
        scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from seed_data import seed_database
        seed_database()
        session.close()
        session = SessionLocal()

    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="module")
def admin_user(db: Session) -> User:
    user = db.query(User).filter(User.role == UserRole.ADMIN).first()
    assert user is not None, "Admin user should exist in DB seed"
    return user

@pytest.fixture(scope="module")
def it_manager_user(db: Session) -> User:
    user = db.query(User).filter(User.role == UserRole.IT_ASSET_MANAGER).first()
    assert user is not None, "IT Manager user should exist in DB seed"
    return user

@pytest.fixture(scope="module")
def employee_user(db: Session) -> User:
    user = db.query(User).filter(User.role == UserRole.EMPLOYEE).first()
    assert user is not None, "Employee user should exist in DB seed"
    return user

@pytest.fixture(scope="module")
def admin_token(admin_user: User) -> str:
    return create_access_token(
        subject=admin_user.id,
        extra_claims={"email": admin_user.email, "role": str(admin_user.role)}
    )

@pytest.fixture(scope="module")
def employee_token(employee_user: User) -> str:
    return create_access_token(
        subject=employee_user.id,
        extra_claims={"email": employee_user.email, "role": str(employee_user.role)}
    )
