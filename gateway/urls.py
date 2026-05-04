from django.contrib import admin
from django.urls import path

from mailer import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", views.health, name="health"),
    path("api/v1/emails/", views.enqueue_email, name="enqueue-email"),
    path("api/v1/emails/<uuid:job_id>/", views.email_status, name="email-status"),
]
