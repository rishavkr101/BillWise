# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the location of the SQLite database file
DATABASE_URL = "sqlite:///./receipts.db"
SQLALCHEMY_DATABASE_URL = DATABASE_URL

# Create the SQLAlchemy engine
# connect_args is needed only for SQLite to allow multi-threaded access
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Each instance of the SessionLocal class will be a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models to inherit from
Base = declarative_base()

# Dependency to get a DB session in path operations
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
