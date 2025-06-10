import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import settings
from src.graph.workflow import create_workflow

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_digest_workflow():
    logger.info("Scheduled digest workflow triggered")
    try:
        workflow = create_workflow()
        result = workflow.invoke({
            "papers": None,
            "summaries": None,
            "digest_html": None,
            "email_status": None,
        })
        sent = sum(1 for e in (result.get("email_status") or []) if e.status == "sent")
        total = len(result.get("email_status") or [])
        logger.info("Digest workflow completed: %d/%d emails sent", sent, total)
    except Exception:
        logger.exception("Digest workflow failed")


def start_scheduler():
    scheduler.add_job(
        run_digest_workflow,
        "cron",
        hour=settings.schedule_hour,
        minute=settings.schedule_minute,
        id="daily_digest",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started: digest runs daily at %02d:%02d",
                settings.schedule_hour, settings.schedule_minute)


def stop_scheduler():
    scheduler.shutdown(wait=False)
