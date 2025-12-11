from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field, create_engine, Session, select
import hashlib
import secrets
import os

# Use /tmp directory for SQLite on Vercel (serverless environment)
IS_VERCEL = os.getenv("VERCEL", False)
DB_DIR = "/tmp" if IS_VERCEL else "."
DB_URL = f"sqlite:///{DB_DIR}/auth.db"
engine = create_engine(DB_URL, echo=False)

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: Optional[str] = None
    password_hash: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Token(SQLModel, table=True):
    __tablename__ = "tokens"
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_session() -> Session:
    return Session(engine)

def create_db_and_seed(force_recreate: bool = False) -> None:
    """
    Create tables and seed a default user (user / password).
    Set force_recreate=True to remove existing auth.db first.
    """
    if force_recreate and os.path.exists("auth.db"):
        os.remove("auth.db")
    SQLModel.metadata.create_all(engine)

    with get_session() as session:
        stmt = select(User).where(User.username == "user")
        existing = session.exec(stmt).first()
        if not existing:
            u = User(
                username="user",
                email="user@example.com",
                password_hash=_hash_password("password"),
                is_active=True
            )
            session.add(u)
            session.commit()

def authenticate_user(username: str, password: str) -> Optional[User]:
    with get_session() as session:
        stmt = select(User).where(User.username == username)
        user = session.exec(stmt).first()
        if not user:
            return None
        if user.password_hash != _hash_password(password):
            return None
        return user

def create_token_for_user(user_id: int, hours_valid: int = 24) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=hours_valid)
    t = Token(token=token, user_id=user_id, expires_at=expires)
    with get_session() as session:
        session.add(t)
        session.commit()
    return token

def get_user_by_token(token_str: str) -> Optional[User]:
    with get_session() as session:
        stmt = select(Token).where(Token.token == token_str)
        t = session.exec(stmt).first()
        if not t:
            return None
        if t.expires_at < datetime.utcnow():
            return None
        user = session.get(User, t.user_id)
        return user

__all__ = ['User', 'Token', 'create_db_and_seed', 'authenticate_user', 'create_token_for_user', 'get_user_by_token', '_hash_password', 'get_session']