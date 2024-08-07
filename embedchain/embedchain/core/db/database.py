import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base
from dotenv import load_dotenv

load_dotenv()

class DatabaseManager:
    def __init__(self, echo: bool = False):
        self.database_uri = os.environ.get("EMBEDCHAIN_DB_URI").replace("postgresql://", "cockroachdb://")
        self.echo = echo
        self.engine: Engine = None
        self._session_factory = None

    def setup_engine(self) -> None:
        """Initializes the database engine and session factory."""
        if not self.database_uri:
            raise RuntimeError("Database URI is not set. Set the EMBEDCHAIN_DB_URI environment variable.")
        connect_args = {}
        if self.database_uri.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        self.engine = create_engine(self.database_uri, echo=self.echo, connect_args=connect_args)
        self._session_factory = scoped_session(sessionmaker(bind=self.engine))
        Base.metadata.bind = self.engine

    def init_db(self) -> None:
        """Creates all tables defined in the Base metadata."""
        if not self.engine:
            raise RuntimeError("Database engine is not initialized. Call setup_engine() first.")
        Base.metadata.create_all(self.engine)

    def get_session(self) -> SQLAlchemySession:
        """Provides a session for database operations."""
        if not self._session_factory:
            raise RuntimeError("Session factory is not initialized. Call setup_engine() first.")
        return self._session_factory()

    def close_session(self) -> None:
        """Closes the current session."""
        if self._session_factory:
            self._session_factory.remove()

    def execute_transaction(self, transaction_block):
        """Executes a block of code within a database transaction."""
        session = self.get_session()
        try:
            transaction_block(session)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            self.close_session()

    def get_messages(self, app_id: str, page_num: int = 1, page_size: int = 10) -> list:
        """Retrieves messages from the database for the given app ID.

        Args:
            app_id (str): The ID of the app.
            page_num (int, optional): The page number. Defaults to 1.
            page_size (int, optional): The page size. Defaults to 10.

        Returns:
            list: List of messages.
        """
        offset = (page_num - 1) * page_size
        query = f"SELECT * FROM ec_chat_history WHERE app_id = '{app_id}' ORDER BY created_at DESC LIMIT {page_size} OFFSET {offset}"
        with self.engine.connect() as conn:
            result = conn.execute(query)
            messages = [dict(row) for row in result]
        return messages

    def get_monthly_usage(self, app_id: str, month: int, year: int):
        """Get the monthly usage for the given month and year.

        Args:
            app_id (str): The app ID.
            month (int): The month.
            year (int): The year.

        Returns:
            dict:
                interactions (int): int,
                total_ratings: int,
                average_rating: float,
                unique_users: int

        """
        # also, we need to get calculated total ratings using rating column 'rating INT', average rating
        query = (f"SELECT COUNT(*) as 'interactions', SUM(rating) as 'total_ratings', AVG(rating) as 'average_rating' "
                 f" COUNT(DISTINCT session_id) as 'unique_users' FROM"
                 f"ec_chat_history WHERE app_id ='{app_id}' AND EXTRACT(MONTH FROM "
                 f"created_at) = {month} AND EXTRACT(YEAR FROM created_at) = {year}")
        with self.engine.connect() as conn:
            result = conn.execute(query)
            monthly_usage = result.fetchone()
        return monthly_usage

    def get_questions(self, app_id: str, page_num: int = 1, page_size: int = 10) -> list:
        """Retrieves questions from the database for the given app ID.

        Args:
            app_id (str): The ID of the app.
            page_num (int, optional): The page number. Defaults to 1.
            page_size (int, optional): The page size. Defaults to 10.

        Returns:
            list: List of questions.
        """
        offset = (page_num - 1) * page_size
        query = f"SELECT question FROM ec_chat_history WHERE app_id = '{app_id}' ORDER BY created_at DESC LIMIT {page_size} OFFSET {offset}"
        with self.engine.connect() as conn:
            result = conn.execute(query)
            questions = [dict(row) for row in result]
        return questions

    def update_helpfulness(self, app_id: str, answer_id: str, was_helpful: bool, rating: int, feedback: str):
        """Update the helpfulness of a response in the database.

        Args:
            app_id (str): The ID of the app.
            answer_id (str): The ID of the answer.
            was_helpful (bool): Whether the response was helpful.
            rating (int): The rating given to the response.
            feedback (str): The feedback provided for the response.
        """
        query = f"UPDATE ec_chat_history SET"
        # check what is not None and create the query accordingly
        if was_helpful is not None:
            query += f" was_helpful = {was_helpful},"
        if rating is not None:
            query += f" rating = {rating},"
        if feedback is not None:
            query += f" feedback = '{feedback}',"
        # remove the trailing comma
        query = query[:-1]
        query += f" WHERE app_id = '{app_id}' AND id = '{answer_id}'"

        with self.engine.connect() as conn:
            conn.execute(query)

        return True

# Singleton pattern to use throughout the application
database_manager = DatabaseManager()


# Convenience functions for backward compatibility and ease of use
def setup_engine(database_uri: str, echo: bool = False) -> None:
    database_manager.database_uri = database_uri
    database_manager.echo = echo
    database_manager.setup_engine()


def alembic_upgrade() -> None:
    """Upgrades the database to the latest version."""
    alembic_config_path = os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
    alembic_cfg = Config(alembic_config_path)
    command.upgrade(alembic_cfg, "head")


def init_db() -> None:
    alembic_upgrade()


def get_session() -> SQLAlchemySession:
    return database_manager.get_session()


def execute_transaction(transaction_block):
    database_manager.execute_transaction(transaction_block)


def get_messages(app_id: str, page_num: int = 1, page_size: int = 10) -> list:
    return database_manager.get_messages(app_id, page_num, page_size)


def get_monthly_usage(app_id: str, month: int, year: int):
    """Get the monthly usage for the given month and year.

    Args:
        app_id (str): The app ID.
        session_id (str): The session ID.
        month (int): The month.
        year (int): The year.

    Returns:
        dict:
            interactions: int,
            total_ratings: int,
            average_rating: float,
            unique_users: int
    """

    return database_manager.get_monthly_usage(app_id, month, year)


def get_questions(app_id: str, page_num: int = 1, page_size: int = 10) -> list:
    return database_manager.get_questions(app_id, page_num, page_size)


def update_response_helpfulness(app_id: str, answer_id: str, was_helpful: bool, rating: int, feedback: str):
    return database_manager.update_helpfulness(app_id, answer_id, was_helpful, rating, feedback)
