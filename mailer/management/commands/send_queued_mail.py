import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from mailer.models import EmailJob
from mailer.services import mark_job_failed, send_email_job


class Command(BaseCommand):
    help = "Sends queued email jobs using the configured SMTP server."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process the current queue and exit.")
        parser.add_argument("--sleep", type=float, default=settings.EMAIL_GATEWAY_WORKER_SLEEP_SECONDS)
        parser.add_argument("--batch-size", type=int, default=settings.EMAIL_GATEWAY_BATCH_SIZE)

    def handle(self, *args, **options):
        while True:
            processed = self.process_batch(options["batch_size"])
            if options["once"]:
                self.stdout.write(self.style.SUCCESS(f"Processed {processed} queued email(s)."))
                return
            if processed == 0:
                time.sleep(options["sleep"])

    def process_batch(self, batch_size):
        processed = 0
        while processed < batch_size:
            job = self.lock_next_job()
            if job is None:
                break
            try:
                send_email_job(job)
                self.stdout.write(self.style.SUCCESS(f"Sent email job {job.id}"))
            except Exception as exc:  # SMTP/network errors must not stop the worker.
                mark_job_failed(job, exc)
                self.stderr.write(self.style.ERROR(f"Email job {job.id} failed: {exc}"))
            processed += 1
        return processed

    def lock_next_job(self):
        now = timezone.now()
        with transaction.atomic():
            queryset = (
                EmailJob.objects.filter(status=EmailJob.Status.PENDING)
                .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
                .order_by("created_at")
            )
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
