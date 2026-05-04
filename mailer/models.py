import uuid

from django.db import models


class EmailJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipients = models.JSONField()
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    last_error = models.TextField(blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.subject} -> {', '.join(self.recipients)}"


def attachment_upload_to(instance, filename):
    return f"email-attachments/{instance.job_id}/{filename}"


class EmailAttachment(models.Model):
    job = models.ForeignKey(EmailJob, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to=attachment_upload_to)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=255, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name
