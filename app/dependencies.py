from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = db.execute(
        text("SELECT id, email, name, is_active FROM users WHERE id = :id"),
        {"id": user_id}
    ).fetchone()
    if not user:
        request.session.clear()
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User disabled")
    return {"id": user.id, "email": user.email, "name": user.name}


def get_user_or_none(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.execute(
        text("SELECT id, email, name, is_active FROM users WHERE id = :id"),
        {"id": user_id}
    ).fetchone()
    if not user or not user.is_active:
        return None
    return {"id": user.id, "email": user.email, "name": user.name}