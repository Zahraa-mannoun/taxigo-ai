"""
Main AI agent chat endpoint.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import ChatRequest, ChatResponse
from services import ai_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, request: Request, db: AsyncSession = Depends(get_db)):
    sio = getattr(request.app.state, "sio", None)
    result = await ai_agent.process_message(
        db=db,
        sio=sio,
        message=payload.message,
        history=payload.conversation_history,
        lang=payload.lang,
    )
    return ChatResponse(**result)
