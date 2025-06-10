import logging
import structlog
from src.config import settings


def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to use structlog
    logging.basicConfig(format="%(message)s", level=logging.INFO)


def get_langfuse_handler():
    if not settings.langfuse_enabled:
        return None

    try:
        from langfuse.callback import CallbackHandler
        handler = CallbackHandler(
            host=settings.langfuse_host,
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
        )
        return handler
    except ImportError:
        logging.warning("langfuse not installed, tracing disabled")
        return None
