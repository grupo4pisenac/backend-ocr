from sqlalchemy import Column, Integer, String, DateTime
from database import Base

class Usuario(Base):
    __tablename__ = "users"

    id    = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    senha = Column(String, nullable=False)

    reset_token         = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime,    nullable=True)