from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified
from rest_framework.response import Response
from .serializers import AssetSerializer, AssetCategorySerializer
from rest_framework.generics import CreateAPIView
from rest_framework.exceptions import PermissionDenied

class CreateAssetView(CreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("you must belong to a company to create asset")
        serializer.save(company=user.company)
    

class CreateCategoryView(CreateAPIView):
    serializer_class = AssetCategorySerializer
    permission_classes = [IsAuthenticated, IsVerified]
    def perform_create(self, serializer):
        user = self.request.user
        if not user.company:
            raise PermissionDenied("you must belong to a company first")
        serializer.save(company=user.company)