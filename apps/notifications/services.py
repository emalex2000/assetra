from django.contrib.auth import get_user_model
from apps.accounts.models import Company
from .models import Notification
from typing import Optional, TYPE_CHECKING
from uuid import UUID


if TYPE_CHECKING:   
    from apps.accounts.models import CustomUser
User = get_user_model()

def create_notification(
        *,
        recipient: "CustomeUser",
        company: Company,
        title: str,
        message: str,
        notification_type: str=Notification.NotificationTypes.GENERAL,
        related_object_id: Optional[UUID] = None,
        related_object_type: Optional[str] = None,
 
) -> Notification:
    """
    create one notification for one user
    """
    return Notification.objects.create(
        recipient=recipient,
        company=company,
        title=title,
        message=message,
        notification_type=notification_type,
        related_object_id=related_object_id,
        related_object_type=related_object_type,
    )