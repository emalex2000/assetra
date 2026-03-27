from rest_framework.permissions import BasePermission

class IsVerified(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_valid
    


class CanAssignAsset(BasePermission):
    def has_permission(self, request, view):
        user = request.user

        if not user.company:
            return False
        
        return user.roles in ["ADMIN", "STAFF"]