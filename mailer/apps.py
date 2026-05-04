from django.apps import AppConfig


class MailerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mailer"

    def ready(self):
        from .background import start_inline_worker

        start_inline_worker()
