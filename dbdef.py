"""
INSTALLER_USERID=rtinstall;INSTALLER_PWD=N0Pa55wrd;MYSQL_DATABASE=rte_db;MYSQL_HOST=localhost;MYSQL_TCP_PORT=50002;SQLALCHEMY_SILENCE_UBER_WARNING=1
"""

from rteapi.core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy import engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

settings = get_settings()


SQLALCHEMY_DATABASE_URL = engine.URL.create(
    "mysql+mysqlconnector",
    username=settings.INSTALLER_USERID,
    password=settings.INSTALLER_PWD,
    host=settings.MYSQL_HOST,
    port=settings.MYSQL_TCP_PORT,
    database=settings.MYSQL_DATABASE,
)
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Remove this in the next commit
