import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import run_turn
from app.api.schemas import ChatRequest, ChatResponse
from app.db.models import ChatMessage, ChatSession
from app.db.session import get_db
from app.llm.base import ChatTurn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

MAX_HISTORY_TURNS = 12


@router.post("", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)) -> ChatResponse:
    session = await db.get(ChatSession, payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == payload.session_id)
        .where(ChatMessage.role.in_(["user", "assistant"]))
        .order_by(ChatMessage.created_at.desc())
        .limit(MAX_HISTORY_TURNS)
    )
    history_rows = list(reversed(history_result.scalars().all()))
    history = [ChatTurn(role=row.role, content=row.content) for row in history_rows]

    user_msg = ChatMessage(session_id=session.id, role="user", content=payload.message)
    db.add(user_msg)
    await db.flush()

    try:
        result = await run_turn(
            db,
            user_message=payload.message,
            history=history,
            requested_skill=payload.skill,
            requested_artifact_format=payload.artifact_format,
        )
    except Exception:
        logger.exception("chat_turn_failed", extra={"event": "chat_turn_failed"})
        await db.rollback()
        raise HTTPException(status_code=502, detail="Failed to generate a response. Please try again.")

    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=result.text,
        provider=result.provider,
        model=result.model,
        skill=result.skill,
        citations=result.citations or None,
        artifact=result.artifact,
        grounded=result.grounded,
    )
    db.add(assistant_msg)

    if session.title is None:
        session.title = payload.message[:80]

    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(message=assistant_msg, fell_back_to_ollama=result.fell_back)
