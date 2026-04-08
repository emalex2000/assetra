from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified, CanAssignAsset
from rest_framework.response import Response
from .serializers import AssetSerializer, AssetCategorySerializer, AssetAssignmentSerializer
from rest_framework.generics import CreateAPIView
from rest_framework.exceptions import PermissionDenied

class CreateAssetView(CreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanAssignAsset]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("you must belong to a company to create asset")
        serializer.save(company=user.company)
    

class CreateCategoryView(CreateAPIView):
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated, IsVerified, CanAssignAsset]
    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("you must belong to a company first")
        serializer.save(company=user.company)


class AssetAssigmentView(CreateAPIView):
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanAssignAsset]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("must belong to a company")
    
        asset = serializer.validated_data.get("asset")
        assignee = serializer.validated_data.get("user")

        if asset.company != user.company:
            raise PermissionDenied("Asset does not belong to your company")
        
        if assignee.company != user.company:
            raise PermissionDenied("User does not belong to your company")
        
        if asset.status != "AVAILABLE":
            raise PermissionDenied("Asset is not available")
        
        assignment = serializer.save(assigned_by=user)
        asset.status = "ASSIGNED"
        asset.current_holder = assignee
        asset.save()