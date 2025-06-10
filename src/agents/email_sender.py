import logging
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.models.db import TeamMember, Digest, SendLog
from src.models.schemas import SendLogEntry

logger = logging.getLogger(__name__)


class EmailSender:
    """Agent that sends the digest email to all active team members via SMTP."""

    def send(self, digest_html: str, db: Session) -> List[SendLogEntry]:
        # Get active team members
        members = db.query(TeamMember).filter(TeamMember.active.is_(True)).all()
        if not members:
            logger.warning("No active team members to send digest to")
            return []

        # Save digest to DB
        digest = Digest(
            date=date.today(),
            html_content=digest_html,
            paper_count=digest_html.count('<div class="paper">'),
        )
        db.add(digest)
        db.flush()

        results = []
        for member in members:
            entry = self._send_to_member(member, digest_html, digest.id, db)
            results.append(entry)

        db.commit()
        sent_count = sum(1 for r in results if r.status == "sent")
        logger.info("Sent digest to %d/%d members", sent_count, len(members))
        return results

    def _send_to_member(
        self, member: TeamMember, html: str, digest_id: int, db: Session
    ) -> SendLogEntry:
        log = SendLog(
            digest_id=digest_id,
            member_id=member.id,
            status="failed",
        )

        try:
            self._send_email(member.email, member.name, html)
            log.status = "sent"
            log.sent_at = datetime.utcnow()
            logger.info("Email sent to %s (%s)", member.name, member.email)
        except Exception as e:
            log.error = str(e)
            logger.exception("Failed to send email to %s", member.email)

        db.add(log)

        return SendLogEntry(
            member_id=member.id,
            member_name=member.name,
            status=log.status,
            error=log.error,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _send_email(self, to_email: str, to_name: str, html: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🧠 AI Research Digest — {date.today().strftime('%B %d, %Y')}"
        msg["From"] = settings.smtp_from
        msg["To"] = f"{to_name} <{to_email}>"

        msg.attach(MIMEText(html, "html"))

        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)

        try:
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, to_email, msg.as_string())
        finally:
            server.quit()
