from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    clicks = Column(Integer, default=0, nullable=False)


class Click(Base):
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True, index=True)
    url_id = Column(Integer, nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String, nullable=True)
    referrer = Column(String, nullable=True)
    clicked_at = Column(DateTime, default=datetime.utcnow, nullable=False)