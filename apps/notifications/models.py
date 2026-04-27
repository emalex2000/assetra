import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationTypes(models.TextChoices):
        ASSET_CREATED = "ASSET_CREATED", "Asset created"
        ASSET_IMPORTED = "ASSET_IMPORTED", "Assets imported"
        ASSET_ASSIGNED = "ASSET_ASSIGNED", "Asset assigned"
        ASSET_RECEIVED = "ASSET_RECEIVED", "Asset received"
        ASSET_TRANSFERRED = "ASSET_TRANSFERRED", "Asset transferred"

        JOIN_REQUEST_CREATED = "JOIN_REQUEST_CREATED", "Join request created"
        JOIN_REQUEST_APPROVED = "JOIN_REQUEST_APPROVED", "Join request approved"
        JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED", "Join request rejected"

        INVITE_CREATED = "INVITE_CREATED", "Invite created"
        ORGANISATION_CREATED = "ORGANISATION_CREATED", "Organisation created"

        GENERAL = "GENERAL", "General"

    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    company = models.ForeignKey('accounts.Company', on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    notification_type = models.CharField(
        max_length=50, choices=NotificationTypes.choices, default=NotificationTypes.GENERAL,
    )
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object_type = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
# Create your models here.
