import mongomock
import pytest
from pymongo.errors import OperationFailure

from app import db as db_module
from app.core.config import settings
from app.services import catalog


@pytest.fixture(autouse=True)
def scripted_mode(monkeypatch):
    """Tests never hit Gemini or a real MongoDB: scripted replies, no Mongo unless `mongo` is used."""
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "decision_engine", "auto")
    monkeypatch.setattr(settings, "mongodb_uri", "")
    catalog.clear_cache()
    yield
    catalog.clear_cache()


class _Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    async def to_list(self, length=None):
        return list(self._cursor)


class _AsyncCollection:
    """The slice of pymongo's async collection API the app uses, backed by mongomock."""

    def __init__(self, coll):
        self._coll = coll

    def find(self, *args, **kwargs):
        return _Cursor(self._coll.find(*args, **kwargs))

    async def aggregate(self, pipeline):
        return _Cursor(self._coll.aggregate(pipeline))

    async def list_search_indexes(self, *args, **kwargs):
        # what a plain (non-Atlas) mongod answers
        raise OperationFailure("$listSearchIndexes stage is only allowed on MongoDB Atlas")

    def __getattr__(self, name):
        method = getattr(self._coll, name)

        async def call(*args, **kwargs):
            return method(*args, **kwargs)

        return call


class _AsyncDatabase:
    def __init__(self, database):
        self._db = database
        self.name = database.name

    def __getattr__(self, name):
        return _AsyncCollection(self._db[name])


@pytest.fixture
def mongo(monkeypatch):
    database = _AsyncDatabase(mongomock.MongoClient()["pocket_fitter_test"])
    for module in ("app.db", "app.services.catalog", "app.services.fittings", "app.api.routes",
                   "app.seed", "app.services.similar"):
        monkeypatch.setattr(f"{module}.get_db", lambda: database)
    return database


assert db_module  # imported so monkeypatch targets exist
