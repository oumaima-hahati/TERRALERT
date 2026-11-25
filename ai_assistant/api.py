"""Standalone FastAPI router for TERRALERT GIS assistant."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .chatbot import answer

router = APIRouter(
    prefix="/chatbot",
    tags=["AI GIS Assistant"],
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.post("/ask")
def ask_chatbot(request: ChatRequest):
    return answer(request.question)
