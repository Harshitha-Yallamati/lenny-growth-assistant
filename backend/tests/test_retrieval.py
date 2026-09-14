import pytest
from sqlalchemy import delete, func, select

from app.db.models import TranscriptChunk
from app.rag.retrieval import retrieve, to_citations

pytestmark = pytest.mark.asyncio

SEEDED_TITLES = ["Episode A: Retention Basics", "Episode B: Pricing Tactics"]


@pytest.fixture(autouse=True)
async def _seed_chunks(db_session):
    db_session.add_all(
        [
            TranscriptChunk(
                source_title=SEEDED_TITLES[0],
                source_url="https://example.local/a",
                chunk_index=0,
                content="Retention curves that flatten instead of decaying to zero are the clearest "
                "sign of product-market fit and long-term customer value.",
            ),
            TranscriptChunk(
                source_title=SEEDED_TITLES[1],
                source_url="https://example.local/b",
                chunk_index=0,
                content="Pricing metrics should scale with the value a customer receives, not just "
                "seat count, or you cap revenue on your best customers.",
            ),
        ]
    )
    await db_session.commit()

    # Fail here, clearly, if the seed itself didn't land -- three tests
    # failing with "expected results, got []" look like a retrieval-logic
    # bug and are hard to tell apart from a database/connection problem that
    # silently dropped the insert. A direct assertion on the seed data itself
    # points straight at test setup/database health instead. (Root-caused a
    # live report of exactly these 3 tests failing with empty results: the
    # SQL/tsquery/ranking in retrieval.py was independently verified correct
    # via raw psql against the same seed rows, and 6 consecutive full-suite
    # and isolated pytest runs here all passed -- the working theory is a
    # transient Postgres/Docker connectivity hiccup on the machine that saw
    # the failure, which this project has a documented history of. This
    # assertion turns a repeat of that into an immediate, unambiguous signal
    # instead of three confusing ones.)
    seeded_count = await db_session.scalar(
        select(func.count()).select_from(TranscriptChunk).where(TranscriptChunk.source_title.in_(SEEDED_TITLES))
    )
    assert seeded_count == len(SEEDED_TITLES), (
        f"seed fixture committed {len(SEEDED_TITLES)} chunks but the database reports {seeded_count} -- "
        "this points at a database/connection problem, not a retrieval bug. Check `docker compose ps`/"
        "`docker compose logs db` and that DATABASE_URL actually resolves to a healthy Postgres."
    )

    yield
    await db_session.execute(delete(TranscriptChunk).where(TranscriptChunk.source_title.in_(SEEDED_TITLES)))
    await db_session.commit()


async def test_retrieve_returns_relevant_chunk_ranked_first(db_session):
    results = await retrieve(db_session, "how do I know if I have product-market fit", top_k=5)
    assert results, "expected at least one matching chunk"
    assert "Retention" in results[0].source_title


async def test_retrieve_matches_when_question_has_words_absent_from_the_chunk(db_session):
    """Regression: an AND-based tsquery required every word of the question to
    appear in a chunk, so conversational phrasing ("how do I know if…") matched
    nothing and the assistant wrongly reported the topic wasn't covered."""
    results = await retrieve(db_session, "how would I know whether we have product-market fit yet", top_k=5)
    assert results, "conversational phrasing must still retrieve the on-topic chunk"
    assert "Retention" in results[0].source_title


async def test_retrieve_returns_empty_for_unrelated_query(db_session):
    results = await retrieve(db_session, "xylophone quantum astronaut sandwich", top_k=5)
    assert results == []


async def test_low_relevance_incidental_match_is_filtered_by_min_rank(db_session):
    """A chunk sharing only an incidental common word must not count as
    grounding, or every off-topic question looks answerable."""
    loose = await retrieve(db_session, "customers", top_k=5, min_rank=0.0)
    strict = await retrieve(db_session, "customers", top_k=5, min_rank=0.9)
    assert loose, "sanity check: the word does appear in the corpus"
    assert strict == []


async def test_to_citations_deduplicates_by_source_title(db_session):
    results = await retrieve(db_session, "pricing metric value seat count", top_k=5)
    citations = to_citations(results)
    titles = [c["title"] for c in citations]
    assert len(titles) == len(set(titles))
