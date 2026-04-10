from rest_framework.permissions import BasePermission
from .models import OrganisationMember

class IsVerified(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_valid
    

def get_user_membership(user, company_id):
    from .models import OrganisationMember

    try:
        return OrganisationMember.objects.get(
            user=user,
            company_id=company_id,
            is_active=True,
        )
    except OrganisationMember.DoesNotExist:
        return None

class CanManageAsset(BasePermission):
    message = "you do not have permission to manage asset for this organisation"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        company_id = view.kwargs.get("organisationId") 
        if not company_id:
            return False

        
        membership = OrganisationMember.objects.filter(
            user=user,
            company_id=company_id,
            is_active=True,
            role__in=["ADMIN", "STAFF"]
        ).first()

        return membership is not None