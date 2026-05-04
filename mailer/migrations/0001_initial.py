# Generated manually for the initial project scaffold.

import django.db.models.deletion
import mailer.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("recipients", models.JSONField()),
                ("subject", models.CharField(max_length=255)),
                ("html_body", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("processing", "Processing"), ("sent", "Sent"), ("failed", "Failed")],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("max_attempts", models.PositiveIntegerField(default=3)),
                ("last_error", models.TextField(blank=True)),
                ("next_attempt_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="EmailAttachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to=mailer.models.attachment_upload_to)),
                ("original_name", models.CharField(max_length=255)),
                ("content_type", models.CharField(blank=True, max_length=255)),
                ("size", models.PositiveBigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="mailer.emailjob"),
                ),
            ],
        ),
    ]
