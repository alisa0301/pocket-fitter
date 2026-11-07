"""Fitting sessions stored in MongoDB (`fittings` collection). No-ops without Mongo."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.db import get_db
from app.schemas import ChatOut, Message

log = logging.getLogger(__name__)


async def save(fitting_id: str | None, messages: list[Message], out: ChatOut) -> str | None:
    """Upsert the conversation and latest answer; returns the fitting id (None without Mongo)."""
    db = get_db()
    if db is None:
        return None
    fitting_id = fitting_id or uuid.uuid4().hex
    now = datetime.now(UTC)
    convo = [m.model_dump() for m in messages] + [{"role": "assistant", "content": out.reply}]
    update: dict = {
        "messages": convo,
        "step": out.step,
        "total_steps": out.total_steps,
        "updated_at": now,
    }
    if out.total_steps and out.step >= out.total_steps:
        update["recommendation"] = out.reply
    try:
        await db.fittings.update_one(
            {"_id": fitting_id},
            {"$set": update, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    except Exception:
        log.exception("Saving fitting %s failed", fitting_id)
        return None
    return fitting_id


async def get(fitting_id: str) -> dict | None:
    db = get_db()
    if db is None:
        return None
    doc = await db.fittings.find_one({"_id": fitting_id})
    if doc:
        doc["id"] = doc.pop("_id")
    return doc
