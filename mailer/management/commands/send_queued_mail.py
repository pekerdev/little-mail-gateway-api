import traceback

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

from mailer.config import get_smtp_config
from mailer.models import EmailJob
from mailer.queue import eligible_jobs, process_batch


class Command(BaseCommand):
    help = "Sends queued email jobs using the configured SMTP server."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process the current queue and exit.")
        parser.add_argument("--sleep", type=float, default=settings.EMAIL_GATEWAY_WORKER_SLEEP_SECONDS)
        parser.add_argument("--batch-size", type=int, default=settings.EMAIL_GATEWAY_BATCH_SIZE)
        parser.add_argument("--dry-run", action="store_true", help="Show eligible jobs without sending them.")

    def handle(self, *args, **options):
        self.verbosity = options["verbosity"]
        self.show_traceback = options["traceback"]
        self.dry_run = options["dry_run"]

        self.log_startup(options)
        if self.dry_run:
            jobs = eligible_jobs()[: options["batch_size"]]
            for job in jobs:
                self.log(1, f"Eligible job {job.id}: to={job.recipients} subject={job.subject!r} attempts={job.attempts}")
            self.stdout.write(self.style.SUCCESS(f"Found {len(jobs)} eligible email(s)."))
            return

        while True:
            processed = process_batch(
                options["batch_size"],
                log_func=self.log_worker_message,
                error_func=self.log_worker_error,
                processing_timeout_seconds=settings.EMAIL_GATEWAY_PROCESSING_TIMEOUT_SECONDS,
            )
            if options["once"]:
                self.stdout.write(self.style.SUCCESS(f"Processed {processed} queued email(s)."))
                return
            if processed == 0:
                self.log(2, f"No eligible jobs. Sleeping {options['sleep']} second(s).")
                import time

                time.sleep(options["sleep"])

    def log_startup(self, options):
        pending = EmailJob.objects.filter(status=EmailJob.Status.PENDING).count()
        processing = EmailJob.objects.filter(status=EmailJob.Status.PROCESSING).count()
        failed = EmailJob.objects.filter(status=EmailJob.Status.FAILED).count()
        eligible = eligible_jobs().count()

        self.log(
            1,
            f"Worker started: settings={settings.SETTINGS_MODULE} db={connection.vendor} "
            f"config={settings.EMAIL_GATEWAY_CONFIG} once={options['once']} dry_run={self.dry_run}",
        )
        self.log(1, f"Queue summary: pending={pending} eligible={eligible} processing={processing} failed={failed}")

        try:
            config = get_smtp_config()
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"SMTP config error: {exc}"))
            if self.show_traceback or self.verbosity >= 3:
                self.stderr.write(traceback.format_exc())
            return

        self.log(
            1,
            f"SMTP config: host={config.host} port={config.port} username={config.username or '<empty>'} "
            f"from={config.from_name} <{config.from_email}> tls={config.use_tls} ssl={config.use_ssl} timeout={config.timeout}",
        )

    def log(self, level, message):
        if self.verbosity >= level:
            self.stdout.write(message)

    def log_worker_message(self, message):
        self.log(1, message)

    def log_worker_error(self, job, exc):
        self.stderr.write(self.style.ERROR(f"Email job {job.id} failed: {exc}"))
        if self.show_traceback or self.verbosity >= 3:
            self.stderr.write(traceback.format_exc())
