import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import (
    SessionCreateRequest,
    SessionDetailResponse,
    SessionRenameRequest,
    SessionResponse,
    SessionSearchHit,
)
from app.db.models import ChatMessage, ChatSession
from app.db.session import get_db

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    payload: SessionCreateRequest, db: AsyncSession = Depends(get_db)
) -> ChatSession:
    session = ChatSession(user_metadata=payload.user_metadata)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[ChatSession]:
    result = await db.execute(select(ChatSession).order_by(ChatSession.updated_at.desc()))
    return list(result.scalars().all())


SNIPPET_RADIUS = 60


def _snippet(content: str, needle: str) -> str:
    """A short window around the first match, so the sidebar can show *why*
    a conversation matched rather than just that it did."""
    idx = content.lower().find(needle.lower())
    if idx == -1:
        return content[: SNIPPET_RADIUS * 2].strip()
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(content), idx + len(needle) + SNIPPET_RADIUS)
    return ("…" if start > 0 else "") + content[start:end].strip() + ("…" if end < len(content) else "")


@router.get("/search", response_model=list[SessionSearchHit])
async def search_sessions(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[SessionSearchHit]:
    """Substring search over conversation titles and message bodies.

    Deliberately a plain ILIKE and nothing to do with the RAG retrieval in
    app/rag/ -- this searches the user's own chat history, where exact
    substring behavior is what people expect from a search box, not ranked
    semantic matching over the transcript corpus.
    """
    like = f"%{q}%"

    title_rows = await db.execute(
        select(ChatSession).where(ChatSession.title.ilike(like)).order_by(ChatSession.updated_at.desc())
    )
    hits: dict[uuid.UUID, SessionSearchHit] = {}
    for s in title_rows.scalars().all():
        hits[s.id] = SessionSearchHit(
            id=s.id, title=s.title, updated_at=s.updated_at, matched_in="title", snippet=None
        )

    message_rows = await db.execute(
        select(ChatMessage, ChatSession)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .where(ChatMessage.content.ilike(like))
        .order_by(ChatSession.updated_at.desc())
        .limit(limit * 4)
    )
    for message, session in message_rows.all():
        # A title match already tells the user why it matched; don't
        # overwrite it with a body snippet.
        if session.id in hits:
            continue
        hits[session.id] = SessionSearchHit(
            id=session.id,
            title=session.title,
            updated_at=session.updated_at,
            matched_in="message",
            snippet=_snippet(message.content, q),
        )

    ordered = sorted(hits.values(), key=lambda h: h.updated_at, reverse=True)
    return ordered[:limit]


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ChatSession:
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.delete(session)
    await db.commit()


@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: uuid.UUID,
    payload: SessionRenameRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    title = payload.title.strip()
    # min_length=1 lets a whitespace-only title through validation, which
    # would blank the sidebar entry rather than rename it.
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be blank")

    session.title = title
    await db.commit()
    await db.refresh(session)
    return session
