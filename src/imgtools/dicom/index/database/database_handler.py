from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from imgtools.dicom.index.models import mapper_registry
from imgtools.logging import logger


class DatabaseHandler:
    """
    Manages database operations using SQLAlchemy ORM.
    """

    def __init__(self, db_path: Path, force_delete: bool = False) -> None:
        """
        Initialize the DatabaseHandler with an SQLite database.

        Parameters
        ----------
        db_path : Path
                Path to the SQLite database file.
        force_delete : bool
                Whether to delete the existing database file if it exists.
        """
        if force_delete and db_path.exists():
            logger.debug("Deleting existing database file.", db_path=db_path)
            db_path.unlink()  # Delete the existing database file

        logger.debug("Creating database engine.", db_path=db_path)
        self.engine = create_engine(f"sqlite:///{db_path}", future=True)
        mapper_registry.metadata.create_all(self.engine)  # Create tables
        self.Session = sessionmaker(bind=self.engine)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Create a new SQLAlchemy session.

        Yields
        ------
        Session
                A SQLAlchemy session object.
        """
        session = self.Session()
        try:
            yield session
            session.commit()  # Commit the transaction
        except Exception:
            session.rollback()  # Rollback on exception
            raise
        finally:
            session.close()
