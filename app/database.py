from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import get_settings


class SimulationSave(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    tick: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload_json: str


engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False}
    if get_settings().database_url.startswith("sqlite")
    else {},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session


def latest_save(session: Session, name: str | None = None) -> SimulationSave | None:
    statement = select(SimulationSave)
    if name:
        statement = statement.where(SimulationSave.name == name)
    statement = statement.order_by(SimulationSave.created_at.desc())
    return session.exec(statement).first()

