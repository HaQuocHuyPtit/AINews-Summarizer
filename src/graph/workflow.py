import logging
from datetime import date
from typing import Any, Dict

import redis
from langgraph.graph import StateGraph

from src.config import settings
from src.agents.paper_searcher import PaperSearcher
from src.agents.paper_summarizer import PaperSummarizer
from src.agents.digest_composer import DigestComposer
from src.agents.email_sender import EmailSender
from src.models.db import Paper, Summary
from src.models.schemas import GraphState
from src.models.session import SessionLocal

logger = logging.getLogger(__name__)


def _get_redis():
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception:
        logger.warning("Redis not available, running without dedup cache")
        return None


def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("=== SEARCH NODE: Finding papers ===")
    redis_client = _get_redis()
    searcher = PaperSearcher(redis_client=redis_client)
    papers = searcher.search()

    # Persist papers to DB
    db = SessionLocal()
    try:
        for paper in papers:
            existing = db.query(Paper).filter(Paper.url == paper.url).first()
            if not existing:
                db.add(Paper(
                    title=paper.title,
                    authors=paper.authors,
                    abstract=paper.abstract,
                    url=paper.url,
                    source=paper.source,
                    published_at=paper.published_at,
                ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist papers")
    finally:
        db.close()

    state["papers"] = papers
    return state


def summarize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("=== SUMMARIZE NODE: Summarizing %d papers ===", len(state["papers"] or []))
    summarizer = PaperSummarizer()
    summaries = summarizer.summarize_all(state["papers"] or [])

    # Persist summaries to DB
    db = SessionLocal()
    try:
        for s in summaries:
            paper = db.query(Paper).filter(Paper.url == s.url).first()
            if paper:
                db.add(Summary(
                    paper_id=paper.id,
                    summary=s.summary,
                    category=s.category,
                    digest_date=date.today(),
                ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to persist summaries")
    finally:
        db.close()

    state["summaries"] = summaries
    return state


def compose_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("=== COMPOSE NODE: Creating digest from %d summaries ===",
                len(state["summaries"] or []))
    composer = DigestComposer()
    html = composer.compose(state["summaries"] or [])
    state["digest_html"] = html
    return state


def email_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("=== EMAIL NODE: Sending digest ===")
    sender = EmailSender()
    db = SessionLocal()
    try:
        results = sender.send(state["digest_html"], db)
        state["email_status"] = results
    except Exception:
        logger.exception("Email sending failed")
        state["email_status"] = []
    finally:
        db.close()
    return state


def create_workflow() -> StateGraph:
    workflow = StateGraph(state_schema=GraphState)

    workflow.add_node("search", search_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("compose", compose_node)
    workflow.add_node("email", email_node)

    workflow.add_edge("search", "summarize")
    workflow.add_edge("summarize", "compose")
    workflow.add_edge("compose", "email")

    workflow.set_entry_point("search")

    return workflow.compile()
