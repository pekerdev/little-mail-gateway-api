import logging
import os
import sys
import threading
import time

from django.conf import settings
from django.db import close_old_connections

from .queue import process_batch


logger = logging.getLogger(__name__)
_started = False


def should_start_inline_worker():
    if not settings.EMAIL_GATEWAY_INLINE_WORKER_ENABLED:
        return False

    skip_commands = {
        "collectstatic",
        "createsuperuser",
        "makemigrations",
        "migrate",
        "send_queued_mail",
        "shell",
        "test",
    }
    if len(sys.argv) > 1 and sys.argv[1] in skip_commands:
        return False

    if settings.DEBUG and "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
        return False

    return True


def start_inline_worker():
    global _started
    if _started or not should_start_inline_worker():
        return

    _started = True
    thread = threading.Thread(target=_worker_loop, name="mail-gateway-inline-worker", daemon=True)
    thread.start()
    logger.info("Inline mail worker started")


def _worker_loop():
    time.sleep(settings.EMAIL_GATEWAY_INLINE_WORKER_START_DELAY_SECONDS)
    while True:
        try:
            close_old_connections()
            processed = process_batch(
                settings.EMAIL_GATEWAY_BATCH_SIZE,
                processing_timeout_seconds=settings.EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS,
            )
            close_old_connections()
        except Exception:
            logger.exception("Inline mail worker loop failed")
            processed = 0

        if processed == 0:
            time.sleep(settings.EMAIL_GATEWAY_WORKER_SLEEP_SECONDS)
