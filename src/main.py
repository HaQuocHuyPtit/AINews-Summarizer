import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.api.routes import router
from src.config import settings
from src.models.db import Base
from src.models.session import engine
from src.observability import setup_logging
from src.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    logger.info("AInsight starting up...")

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")

    # Start scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("AInsight shut down")


app = FastAPI(
    title="AInsight",
    description="Daily AI Research Paper Digest",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
