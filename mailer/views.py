import json
from email.utils import parseaddr

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import EmailAttachment, EmailJob


def _authorized(request):
    expected = settings.EMAIL_GATEWAY_API_KEY
    if not expected:
        return True
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip()
    return token == expected or request.headers.get("X-API-Key") == expected


def _parse_payload(request):
    if request.content_type and request.content_type.startswith("multipart/form-data"):
        raw_recipients = request.POST.get("recipients") or request.POST.get("to")
        subject = request.POST.get("subject", "")
        html_body = request.POST.get("html_body") or request.POST.get("html") or request.POST.get("body", "")
    else:
        data = json.loads(request.body.decode("utf-8") or "{}")
        raw_recipients = data.get("recipients") or data.get("to")
        subject = data.get("subject", "")
        html_body = data.get("html_body") or data.get("html") or data.get("body", "")

    if isinstance(raw_recipients, str):
        stripped = raw_recipients.strip()
        if stripped.startswith("["):
            recipients = json.loads(stripped)
        else:
            recipients = [item.strip() for item in stripped.split(",") if item.strip()]
    elif isinstance(raw_recipients, list):
        recipients = raw_recipients
    else:
        recipients = []

    return recipients, subject.strip(), html_body


def _validate_recipients(recipients):
    valid = []
    for recipient in recipients:
        if not isinstance(recipient, str):
            continue
        _, email = parseaddr(recipient)
        if email and "@" in email:
            valid.append(recipient.strip())
    return valid


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@require_POST
def enqueue_email(request):
    if not _authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        recipients, subject, html_body = _parse_payload(request)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)

    recipients = _validate_recipients(recipients)
    if not recipients:
        return JsonResponse({"error": "recipients_required"}, status=400)
    if not subject:
        return JsonResponse({"error": "subject_required"}, status=400)
    if not html_body:
        return JsonResponse({"error": "html_body_required"}, status=400)

    job = EmailJob.objects.create(recipients=recipients, subject=subject, html_body=html_body)
    for uploaded_file in request.FILES.getlist("attachments"):
        EmailAttachment.objects.create(
            job=job,
            file=uploaded_file,
            original_name=uploaded_file.name,
            content_type=uploaded_file.content_type or "",
            size=uploaded_file.size,
        )

    return JsonResponse(
        {
            "id": str(job.id),
            "status": job.status,
            "recipients": job.recipients,
            "attachments": job.attachments.count(),
        },
        status=202,
    )


@require_GET
def email_status(request, job_id):
    if not _authorized(request):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        job = EmailJob.objects.get(id=job_id)
    except EmailJob.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    return JsonResponse(
        {
            "id": str(job.id),
            "status": job.status,
            "recipients": job.recipients,
            "subject": job.subject,
            "attempts": job.attempts,
            "last_error": job.last_error,
            "created_at": job.created_at.isoformat(),
            "sent_at": job.sent_at.isoformat() if job.sent_at else None,
            "attachments": job.attachments.count(),
        }
    )
