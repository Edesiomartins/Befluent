import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import get_db
from app.core.security import hash_password
from app.main import app
from app.models import Base,User,UserPreference
from app.services.seed import seed_languages
engine=create_engine("sqlite://",connect_args={"check_same_thread":False},poolclass=StaticPool)
TestingSession=sessionmaker(bind=engine,expire_on_commit=False)
def override_db():
    db=TestingSession()
    try: yield db
    finally: db.close()
app.dependency_overrides[get_db]=override_db
@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestingSession() as db:
        seed_languages(db); user=User(email="admin@befluent.local",name="Admin",password_hash=hash_password("senha-segura")); db.add(user); db.flush(); db.add(UserPreference(user_id=user.id)); db.commit()
    yield
@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def auth(client):
    response=client.post("/api/v1/auth/login",json={"email":"admin@befluent.local","password":"senha-segura"})
    assert response.status_code==200
    return {"X-CSRF-Token":client.cookies.get("csrf_token")}
