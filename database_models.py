from sqlalchemy import Column, Integer, String
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    refresh_token = Column(String)
    discord_id = Column(String, unique=True, index=True)
    username = Column(String)
    email = Column(String, unique=True, index=True)
    avatar = Column(String)