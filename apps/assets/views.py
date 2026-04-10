from .models import AssetCategories
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified, CanManageAsset
from rest_framework.response import Response
from .serializers import AssetSerializer, AssetCategorySerializer, AssetAssignmentSerializer
from rest_framework.generics import CreateAPIView, ListCreateAPIView
from rest_framework.exceptions import PermissionDenied, NotFound
from apps.accounts.models import Company, OrganisationMember

class CreateAssetView(CreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("you must belong to a company to create asset")
        serializer.save(company=user.company)
    

class AssetCategoryListCreateView(ListCreateAPIView):
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        if hasattr(self, "_company"):
            return self._company
        
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found")
        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True
            ).exists()
        
        if not is_member:
            raise PermissionError("you are not a member of this organisation")
        self._company = company
        return self._company
        
    def get_queryset(self):
        return AssetCategories.objects.filter(
            company=self.get_company()
        ).order_by("name")
    
    def perform_create(self, serializer):
        serializer.save(
            company=self.get_company()
        )

class AssetAssigmentView(CreateAPIView):
    serializer_class = AssetAssignmentSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

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