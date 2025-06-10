from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    topics = Column(ARRAY(String), default=list)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    send_logs = relationship("SendLog", back_populates="member")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    authors = Column(ARRAY(String), default=list)
    abstract = Column(Text)
    url = Column(String(512), unique=True, nullable=False)
    source = Column(String(50))  # "arxiv", "semantic_scholar"
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    summaries = relationship("Summary", back_populates="paper")


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False)
    summary = Column(Text, nullable=False)
    category = Column(String(100))
    digest_date = Column(Date, nullable=False)

    paper = relationship("Paper", back_populates="summaries")


class Digest(Base):
    __tablename__ = "digests"

    id = Column(Integer, primary_key=True)
    date = Column(Date, unique=True, nullable=False)
    html_content = Column(Text, nullable=False)
    paper_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    send_logs = relationship("SendLog", back_populates="digest")


class SendLog(Base):
    __tablename__ = "send_log"

    id = Column(Integer, primary_key=True)
    digest_id = Column(Integer, ForeignKey("digests.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("team_members.id"), nullable=False)
    status = Column(String(20), nullable=False)  # "sent", "failed", "bounced"
    sent_at = Column(DateTime)
    error = Column(Text)

    digest = relationship("Digest", back_populates="send_logs")
    member = relationship("TeamMember", back_populates="send_logs")
