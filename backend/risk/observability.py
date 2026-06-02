"""
Observability module for LangFuse integration.
"""

import os
import logging
from contextlib import contextmanager

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@contextmanager
def observe():
    """Context manager for observability with LangFuse."""
    has_langfuse = bool(os.getenv("LANGFUSE_SECRET_KEY"))
    if not has_langfuse:
        yield
        return

    langfuse_client = None
    try:
        import logfire
        from langfuse import get_client

        logfire.configure(service_name="alex_risk_agent", send_to_logfire=False)
        logfire.instrument_openai_agents()
        langfuse_client = get_client()
    except Exception as e:
        logger.error(f"Observability setup failed: {e}")
        langfuse_client = None

    try:
        yield
    finally:
        if langfuse_client:
            try:
                langfuse_client.flush()
                langfuse_client.shutdown()
            except Exception as e:
                logger.error(f"Failed to flush traces: {e}")
