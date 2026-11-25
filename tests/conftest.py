import pytest

from ai_sql.db import connect
from data.create_db import create_db


@pytest.fixture
def db_path(tmp_path):
    """A fresh, small copy of the retail database for every test."""
    return create_db(tmp_path / "test.db", n_orders=300)


@pytest.fixture
def conn(db_path):
    connection = connect(db_path)
    yield connection
    connection.close()


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch):
    """Tests never call the real OpenAI API."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
