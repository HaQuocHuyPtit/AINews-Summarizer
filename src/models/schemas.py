from datetime import date, datetime
from typing import List, Optional, TypedDict

from pydantic import BaseModel, EmailStr


# --- Pydantic schemas for API / validation ---

class PaperSchema(BaseModel):
    title: str
    authors: List[str] = []
    abstract: str
    url: str
    source: str
    published_at: Optional[datetime] = None


class SummarySchema(BaseModel):
    title: str
    summary: str
    category: Optional[str] = None
    url: str


class TeamMemberCreate(BaseModel):
    name: str
    email: str
    topics: List[str] = []


class TeamMemberResponse(BaseModel):
    id: int
    name: str
    email: str
    topics: List[str]
    active: bool

    model_config = {"from_attributes": True}


class DigestResponse(BaseModel):
    id: int
    date: date
    paper_count: Optional[int]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SendLogEntry(BaseModel):
    member_id: int
    member_name: str
    status: str
    error: Optional[str] = None


# --- LangGraph State ---

class GraphState(TypedDict):
    papers: Optional[List[PaperSchema]]
    summaries: Optional[List[SummarySchema]]
    digest_html: Optional[str]
    email_status: Optional[List[SendLogEntry]]
