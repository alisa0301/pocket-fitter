"""MongoDB access. Everything works without Mongo: get_db() returns None when MONGODB_URI is unset."""
from __future__ import annotations

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings

_client: AsyncMongoClient | None = None


def get_db() -> AsyncDatabase | None:
    global _client
    if not settings.mongodb_uri:
        return None
    if _client is None:
        _client = AsyncMongoClient(
            settings.mongodb_uri, appname="pocket-fitter", serverSelectionTimeoutMS=3000
        )
    return _client[settings.mongodb_db]


async def close() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
