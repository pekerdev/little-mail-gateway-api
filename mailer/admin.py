from django.contrib import admin

from .models import EmailAttachment, EmailJob


class EmailAttachmentInline(admin.TabularInline):
    model = EmailAttachment
    extra = 0
    readonly_fields = ("original_name", "content_type", "size", "created_at")


@admin.register(EmailJob)
class EmailJobAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "status", "attempts", "created_at", "sent_at")
    list_filter = ("status", "created_at", "sent_at")
    search_fields = ("subject", "recipients", "last_error")
    readonly_fields = ("created_at", "updated_at", "locked_at", "sent_at")
    inlines = [EmailAttachmentInline]


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "job", "content_type", "size", "created_at")
    search_fields = ("original_name", "job__subject")
