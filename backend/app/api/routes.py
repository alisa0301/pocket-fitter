from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class EchoIn(BaseModel):
    message: str


class EchoOut(BaseModel):
    reply: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/echo", response_model=EchoOut)
def echo(body: EchoIn) -> EchoOut:
    # Заглушка: замените на вызов модели / вашу бизнес-логику
    return EchoOut(reply=f"Backend received: {body.message}")
