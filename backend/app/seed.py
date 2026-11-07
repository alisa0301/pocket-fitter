"""Load Takomo's catalog into MongoDB and create indexes.

    cd backend && MONGODB_URI=... uv run python -m app.seed
"""
import asyncio

from app.db import close, get_db
from app.services import catalog


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


async def main() -> None:
    try:
        await seed()
    finally:
        await close()


if __name__ == "__main__":
    asyncio.run(main())
