from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool
import os
#тут короче мы пишем логин пароль и адрес с портом, а в конце название бд

URL_DATABASE = "postgresql://postgres:@localhost:5432/vendo"

engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()