from rest_framework.permissions import BasePermission

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

class CanAssignAsset(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        company_id = request.headers.get("X-Company-ID") 

        if not company_id:
            return False
        
        membership = get_user_membership(user, company_id)
        if not membership:
            return False
        return membership.role in ["ADMIN", "STAFF"]