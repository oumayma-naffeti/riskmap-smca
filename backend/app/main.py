from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (nécessaire pour enregistrer les tables)
from .database import Base, engine, get_db
from .routers import assets, auth, processes, risks, users

app = FastAPI(title="RiskMap-SMCA", version="0.2.0",
              description="Identification et cartographie des risques d'un SMCA (ISO 22301)")


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(assets.router)
app.include_router(processes.router)
app.include_router(risks.router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
