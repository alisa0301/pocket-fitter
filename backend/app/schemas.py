from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatIn(BaseModel):
    messages: list[Message]
    fitting_id: str | None = None


class ChatOut(BaseModel):
    reply: str
    suggestions: list[str] = []
    step: int = 0
    total_steps: int = 0
    fitting_id: str | None = None  # set when the fitting is saved to MongoDB
