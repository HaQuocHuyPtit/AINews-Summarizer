import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from src.graph.workflow import create_workflow
from src.models.db import TeamMember, Digest, SendLog
from src.models.schemas import TeamMemberCreate, TeamMemberResponse, DigestResponse
from src.models.session import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Workflow ---

def _run_workflow():
    workflow = create_workflow()
    workflow.invoke({
        "papers": None,
        "summaries": None,
        "digest_html": None,
        "email_status": None,
    })


@router.post("/run", tags=["workflow"])
def trigger_run(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_workflow)
    return {"status": "started", "message": "Digest workflow triggered in background"}


# --- Team Members ---

@router.get("/members", response_model=List[TeamMemberResponse], tags=["members"])
def list_members(db: Session = Depends(get_db)):
    return db.query(TeamMember).order_by(TeamMember.name).all()


@router.post("/members", response_model=TeamMemberResponse, tags=["members"])
def create_member(member: TeamMemberCreate, db: Session = Depends(get_db)):
    existing = db.query(TeamMember).filter(TeamMember.email == member.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    db_member = TeamMember(
        name=member.name,
        email=member.email,
        topics=member.topics,
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.patch("/members/{member_id}/toggle", response_model=TeamMemberResponse, tags=["members"])
def toggle_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(TeamMember).get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    member.active = not member.active
    db.commit()
    db.refresh(member)
    return member


@router.delete("/members/{member_id}", tags=["members"])
def delete_member(member_id: int, db: Session = Depends(get_db)):
    member = db.query(TeamMember).get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"status": "deleted"}


# --- Digests ---

@router.get("/digests", response_model=List[DigestResponse], tags=["digests"])
def list_digests(limit: int = 30, db: Session = Depends(get_db)):
    return db.query(Digest).order_by(Digest.date.desc()).limit(limit).all()


@router.get("/digests/{digest_id}", tags=["digests"])
def get_digest(digest_id: int, db: Session = Depends(get_db)):
    digest = db.query(Digest).get(digest_id)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")

    logs = db.query(SendLog).filter(SendLog.digest_id == digest_id).all()
    return {
        "id": digest.id,
        "date": digest.date,
        "paper_count": digest.paper_count,
        "html_content": digest.html_content,
        "send_log": [
            {
                "member_id": log.member_id,
                "status": log.status,
                "sent_at": log.sent_at,
                "error": log.error,
            }
            for log in logs
        ],
    }
