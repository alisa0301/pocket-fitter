"""Placeholder for the Jeff decision model.

Fill this in once we have Jeff's real API (endpoint, auth, request/response format).
Contract the rest of the app expects: take a PlayerProfile, choose from app.catalog,
return a Recommendation (with engine="jeff"). Enable with DECISION_ENGINE=jeff and JEFF_URL.
"""

from app.schemas import PlayerProfile, Recommendation


async def decide(profile: PlayerProfile) -> Recommendation:
    raise NotImplementedError("Jeff integration not implemented yet: see app/decision/jeff.py")
