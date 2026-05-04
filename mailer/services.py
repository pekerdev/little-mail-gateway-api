from email.utils import formataddr

from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

from .config import get_smtp_config
from .models import EmailJob


def send_email_job(job: EmailJob) -> None:
    config = get_smtp_config()
    connection = get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=config.timeout,
    )
    message = EmailMultiAlternatives(
        subject=job.subject,
        body="Este correo requiere un cliente compatible con HTML.",
        from_email=formataddr((config.from_name, config.from_email)),
        to=job.recipients,
        connection=connection,
    )
    message.attach_alternative(job.html_body, "text/html")

    for attachment in job.attachments.all():
        with attachment.file.open("rb") as fh:
            message.attach(attachment.original_name, fh.read(), attachment.content_type or None)

    message.send(fail_silently=False)

    job.status = EmailJob.Status.SENT
    job.sent_at = timezone.now()
    job.locked_at = None
    job.last_error = ""
    job.save(update_fields=["status", "sent_at", "locked_at", "last_error", "updated_at"])


def mark_job_failed(job: EmailJob, error: Exception) -> None:
    job.attempts += 1
    job.last_error = str(error)
    job.locked_at = None
    if job.attempts >= job.max_attempts:
        job.status = EmailJob.Status.FAILED
        job.next_attempt_at = None
    else:
        job.status = EmailJob.Status.PENDING
        delay_seconds = min(300, 30 * (2 ** (job.attempts - 1)))
        job.next_attempt_at = timezone.now() + timezone.timedelta(seconds=delay_seconds)
    job.save(update_fields=["attempts", "last_error", "locked_at", "status", "next_attempt_at", "updated_at"])
