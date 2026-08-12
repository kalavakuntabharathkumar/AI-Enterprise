import os
from datetime import datetime, timedelta, timezone
from typing import Any, Generator

import bcrypt
import jwt
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./enterprise.db"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
ALGORITHM = "HS256"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
security = HTTPBearer(auto_error=False)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")
    status = Column(String, default="active")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(String, default="todo")
    priority = Column(String, default="medium")
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class LoginRequest(BaseModel):
    email: str
    password: str


class ResourceRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    title: str | None = None
    priority: str | None = None
    project_id: int | None = None
    assignee_id: int | None = None


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


app = FastAPI(title="AI Enterprise Management Platform")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(db_session),
) -> User:
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(User, int(payload.get("sub", "0")))
    except (jwt.PyJWTError, ValueError, TypeError):
        raise HTTPException(401, "Invalid or expired token")
    if not user:
        raise HTTPException(401, "User not found")
    return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dependency


def serialize(row: Any) -> dict:
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def seed(db: Session) -> None:
    if db.query(User).count():
        return
    users = [
        User(name="Admin User", email="admin@example.com", password_hash=hash_password("admin123"), role="admin"),
        User(name="Manager User", email="manager@example.com", password_hash=hash_password("manager123"), role="manager"),
        User(name="Employee User", email="employee@example.com", password_hash=hash_password("employee123"), role="employee"),
    ]
    db.add_all(users)
    db.flush()
    projects = [
        Project(name="AI Copilot", description="Internal AI assistant", status="active", owner_id=users[1].id),
        Project(name="Platform UX", description="Dashboard improvements", status="active", owner_id=users[1].id),
    ]
    db.add_all(projects)
    db.flush()
    db.add_all([
        Task(title="Connect LLM", status="todo", priority="high", project_id=projects[0].id, assignee_id=users[2].id),
        Task(title="Build dashboard", status="in-progress", priority="medium", project_id=projects[1].id, assignee_id=users[2].id),
    ])
    db.commit()


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)


@app.get("/api/auth/demo-accounts")
def demo_accounts(db: Session = Depends(db_session)):
    return [{"email": u.email, "role": u.role} for u in db.query(User).all()]


@app.post("/api/auth/login")
def login(payload: LoginRequest, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": serialize(user)}


@app.get("/api/auth/me")
def auth_me(user: User = Depends(current_user)):
    return serialize(user)


def list_resource(model: Any, user: User, db: Session):
    return [serialize(row) for row in db.query(model).order_by(model.id.desc()).all()]


def resource_routes(path: str, model: Any, read_roles=("admin", "manager", "employee"), write_roles=("admin", "manager"), delete_roles=("admin",)):
    @app.get(f"/api/{path}")
    def list_items(db: Session = Depends(db_session), user: User = Depends(require_roles(*read_roles))):
        return list_resource(model, user, db)

    @app.get(f"/api/{path}/{{item_id}}")
    def get_item(item_id: int, db: Session = Depends(db_session), user: User = Depends(require_roles(*read_roles))):
        row = db.get(model, item_id)
        if not row:
            raise HTTPException(404, "Record not found")
        return serialize(row)

    @app.post(f"/api/{path}", status_code=201)
    def create_item(payload: ResourceRequest, db: Session = Depends(db_session), user: User = Depends(require_roles(*write_roles))):
        data = payload.model_dump(exclude_none=True)
        allowed = {c.name for c in model.__table__.columns if c.name != "id"}
        row = model(**{k: v for k, v in data.items() if k in allowed})
        db.add(row)
        db.commit()
        db.refresh(row)
        return serialize(row)

    @app.put(f"/api/{path}/{{item_id}}")
    def update_item(item_id: int, payload: ResourceRequest, db: Session = Depends(db_session), user: User = Depends(require_roles(*write_roles))):
        row = db.get(model, item_id)
        if not row:
            raise HTTPException(404, "Record not found")
        allowed = {c.name for c in model.__table__.columns if c.name != "id"}
        for key, value in payload.model_dump(exclude_none=True).items():
            if key in allowed:
                setattr(row, key, value)
        db.commit()
        db.refresh(row)
        return serialize(row)

    @app.delete(f"/api/{path}/{{item_id}}")
    def delete_item(item_id: int, db: Session = Depends(db_session), user: User = Depends(require_roles(*delete_roles))):
        row = db.get(model, item_id)
        if not row:
            raise HTTPException(404, "Record not found")
        db.delete(row)
        db.commit()
        return {"deleted": item_id}


resource_routes("employees", User, write_roles=("admin",), delete_roles=("admin",))
resource_routes("projects", Project)
resource_routes("tasks", Task)


@app.post("/api/copilot")
def copilot(payload: CopilotRequest, db: Session = Depends(db_session), user: User = Depends(current_user)):
    projects = [serialize(p) for p in db.query(Project).all()]
    tasks = [serialize(t) for t in db.query(Task).all()]
    context = {"projects": projects, "tasks": tasks}
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"answer": f"Demo mode: I received '{payload.question}'. Current context contains {len(projects)} projects and {len(tasks)} tasks."}
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are an enterprise operations copilot. Use only the supplied application context."},
            {"role": "user", "content": f"Context: {context}\nQuestion: {payload.question}"},
        ],
    )
    return {"answer": response.choices[0].message.content}
