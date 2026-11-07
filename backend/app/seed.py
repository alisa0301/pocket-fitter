"""Load Takomo's catalog into MongoDB and create indexes.

    cd backend && MONGODB_URI=... uv run python -m app.seed
"""
import asyncio

from pymongo.errors import PyMongoError
from pymongo.operations import SearchIndexModel

from app.db import close, get_db
from app.services import catalog, similar


async def seed() -> None:
    db = get_db()
    if db is None:
        raise SystemExit("MONGODB_URI is not set")
    products, meta = catalog.to_documents(catalog.load_file())
    for p in products:  # 43 small docs
        await db.products.replace_one({"_id": p["_id"]}, p, upsert=True)
    await db.products.delete_many({"_id": {"$nin": [p["_id"] for p in products]}})
    await db.catalog_meta.replace_one({"_id": meta["_id"]}, meta, upsert=True)
    await db.products.create_index([("kind", 1), ("order", 1)])
    await db.fittings.create_index("updated_at")
    print(f"Seeded {len(products)} products into {db.name}.products")
    await seed_golfers(db)


async def seed_golfers(db, batch: int = 2000) -> None:
    """Takomo's train golfers (embedding + reference fit) and the Atlas Vector Search index."""
    golfers = similar.load_file()
    await db.golfers.delete_many({})
    for i in range(0, len(golfers), batch):
        await db.golfers.insert_many(golfers[i : i + batch])
    print(f"Seeded {len(golfers)} golfers into {db.name}.golfers")
    definition = {"fields": [{"type": "vector", "path": "embedding",
                              "numDimensions": similar.DIM, "similarity": "euclidean"}]}
    try:
        existing = [ix["name"] for ix in await (await db.golfers.list_search_indexes()).to_list(None)]
        if similar.INDEX_NAME in existing:
            await db.golfers.update_search_index(similar.INDEX_NAME, definition)
        else:
            await db.golfers.create_search_index(
                SearchIndexModel(definition=definition, name=similar.INDEX_NAME, type="vectorSearch")
            )
        print(f"Vector search index '{similar.INDEX_NAME}' requested (Atlas builds it in ~1 min)")
    except PyMongoError as exc:  # not Atlas: plain mongod has no search indexes
        print(f"Could not create the vector search index ({exc}); in-memory search will be used")


async def main() -> None:
    try:
        await seed()
    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
