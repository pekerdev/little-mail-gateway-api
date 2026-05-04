import logging

from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import EmailJob
from .services import mark_job_failed, send_email_job


logger = logging.getLogger(__name__)


def eligible_jobs():
    now = timezone.now()
    return (
        EmailJob.objects.filter(status__in=[EmailJob.Status.PENDING, EmailJob.Status.FAILED])
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .order_by("created_at")
    )


def lock_next_job():
    now = timezone.now()
    with transaction.atomic():
        queryset = eligible_jobs()
        if connection.features.has_select_for_update:
            select_kwargs = {}
            if connection.features.has_select_for_update_skip_locked:
                select_kwargs["skip_locked"] = True
            queryset = queryset.select_for_update(**select_kwargs)

        job = queryset.first()
        if job is None:
            return None

        job.status = EmailJob.Status.PROCESSING
        job.locked_at = now
        job.save(update_fields=["status", "locked_at", "updated_at"])
        return job


def release_stale_processing_jobs(timeout_seconds):
    stale_before = timezone.now() - timezone.timedelta(seconds=timeout_seconds)
    return EmailJob.objects.filter(
        status=EmailJob.Status.PROCESSING,
        locked_at__lt=stale_before,
    ).update(status=EmailJob.Status.PENDING, locked_at=None)


def process_batch(batch_size, log_func=None, error_func=None, processing_timeout_seconds=None):
    if processing_timeout_seconds is not None:
        released = release_stale_processing_jobs(processing_timeout_seconds)
        if released and log_func:
            log_func(f"Released {released} stale processing email job(s)")

    processed = 0
    while processed < batch_size:
        job = lock_next_job()
        if job is None:
            break
        try:
            if log_func:
                log_func(
                    f"Sending job {job.id}: to={job.recipients} subject={job.subject!r} "
                    f"attachments={job.attachments.count()} attempt={job.attempts + 1}/{job.max_attempts}"
                )
            send_email_job(job)
            if log_func:
                log_func(f"Sent email job {job.id}")
        except Exception as exc:  # SMTP/network errors must not stop queue processing.
            mark_job_failed(job, exc)
            logger.exception("Email job %s failed: %s", job.id, exc)
            if error_func:
                error_func(job, exc)
            elif log_func:
                log_func(f"Email job {job.id} failed: {exc}")
        processed += 1
    return processed
