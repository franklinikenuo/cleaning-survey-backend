from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ------------------------------------------------------------
# DATABASE URL (PostgreSQL on Render)
# ------------------------------------------------------------

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# ------------------------------------------------------------
# ENGINE (PostgreSQL compatible)
# ------------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# ------------------------------------------------------------
# SESSION
# ------------------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ------------------------------------------------------------
# BASE MODEL
# ------------------------------------------------------------

Base = declarative_base()
