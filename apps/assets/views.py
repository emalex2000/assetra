from .models import Asset, AssetCategories, AssetImportSession
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified, CanManageAsset
from rest_framework.response import Response
from .serializers import (
    AssetSerializer, 
    AssetCategorySerializer, 
    AssetAssignmentSerializer, 
    AssetListSerializer, 
    AssetImportUploadSerializer,
    AssetImportMappingSerializer,
)
from rest_framework.generics import CreateAPIView, ListCreateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound
from apps.accounts.models import Company, OrganisationMember
from .import_parser import extract_excel_metadata
from apps.assets.services.import_mappings import build_normalized_rows
from apps.assets.services.import_validation import validate_import_rows
from apps.assets.services.import_commit import commit_import_rows
from rest_framework import status
from .models import AssetImportColumnMapping, AssetImportRow


class CreateAssetView(CreateAPIView):
    serializer_class = AssetSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")
        try:
            return Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("company not found")
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self.get_company()

        return context

    def perform_create(self, serializer):
        serializer.save(company=self.get_company())
    

class AssetListView(ListAPIView):
    serializer_class = AssetListSerializer
    permission_classes  = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            return Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("company not found")
        

    def get_queryset(self):
        company = self.get_company()
        return (
            Asset.objects.filter(company=company)
            .select_related("category", "company", "current_holder")
            .order_by("-created_at")
        )

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
            raise PermissionDenied("you are not a member of this organisation")
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


class AssetImportUploadView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("company not found")
        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
        ).exists()

        if not is_member:
            raise PermissionDenied("must be a member of the organisation")
        
        return company


    def post(self, request, *args, **kwargs):
        serializer = AssetImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = self.get_company()
        uploaded_file = serializer.validated_data["file"]

        import_session = AssetImportSession.objects.create(
            company=company,
            uploaded_by=request.user,
            original_file=uploaded_file,
            original_filename=uploaded_file.name,
            status="UPLOADED",
        )

        with import_session.original_file.open("rb") as f:
            metadata = extract_excel_metadata(f)
        import_session.total_rows = metadata["total_rows"]
        import_session.save(update_fields=["total_rows", "updated_at"])

        return Response(
            {
                "import_id": str(import_session.import_id),
                "filename": import_session.original_filename,
                "sheet_name": metadata["sheet_name"],
                "headers": metadata["headers"],
                "total_rows": metadata["total_rows"],
                "preview_rows": metadata["preview_rows"],
                "status": import_session.status,
            }, status=status.HTTP_201_CREATED,
        )


class AssetImportMappingView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound('organisation not found')
        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            is_active=True,
            company=company,
        ).exists()

        if not is_member:
            raise PermissionDenied('user not part of the organisation')
        
        return company
    
    def get_import_session(self, company):
        import_id = self.kwargs.get("importId")

        try:
            return AssetImportSession.objects.get(import_id=import_id, company=company)
        except AssetImportSession.DoesNotExist:
            raise NotFound('import session not found')
        
    def post(self, request, *args, **kwargs):
        serializer = AssetImportMappingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company = self.get_company()
        import_session = self.get_import_session(company)
        mappings = serializer.validated_data['mappings']

        #clear mappings  if remapping
        import_session.column_mappings.all().delete()
        import_session.rows.all().delete()

        mapping_objs = []
        for source_column, target_field in mappings.items():
            mapping_objs.append(
                AssetImportColumnMapping(
                    session=import_session,
                    source_column=source_column,
                    target_field=target_field if target_field else None,
                    is_skipped=not bool(target_field)
                )
            )

        AssetImportColumnMapping.objects.bulk_create(mapping_objs)

        with import_session.original_file.open("rb") as f:
            normalized_rows = build_normalized_rows(f, mappings)
        
        row_objs = []
        for row in normalized_rows:
            row_objs.append(
                AssetImportRow(
                   session=import_session,
                   row_number=row["row_number"],
                   raw_data=row["raw_data"], 
                   normalized_data=row["normalized_data"],
                   is_valid=False,
                   errors=[],
                )
            )
        AssetImportRow.objects.bulk_create(row_objs, batch_size=500)
        import_session.status = "MAPPED"
        import_session.save(update_fields=["status", "updated_at"])
        preview_rows = normalized_rows[:5]

        return Response(
            {
                "import_id": str(import_session.import_id),
                "status": import_session.status,
                "mapped_columns": mappings,
                "total_rows": len(normalized_rows),
                "preview_rows": preview_rows,
            }, status=status.HTTP_200_OK,
        )
    

class AssetImportValidationView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found.")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organisation.")

        return company

    def get_import_session(self, company):
        import_id = self.kwargs.get("importId")

        try:
            return AssetImportSession.objects.get(import_id=import_id, company=company)
        except AssetImportSession.DoesNotExist:
            raise NotFound("Import session not found.")

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        import_session = self.get_import_session(company)

        result = validate_import_rows(import_session)

        return Response(result, status=status.HTTP_200_OK)


class AssetImportCommitView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("Company not found.")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
        ).exists()

        if not is_member:
            raise PermissionDenied("You are not a member of this organisation.")

        return company

    def get_import_session(self, company):
        import_id = self.kwargs.get("importId")

        try:
            return AssetImportSession.objects.get(import_id=import_id, company=company)
        except AssetImportSession.DoesNotExist:
            raise NotFound("Import session not found.")

    def post(self, request, *args, **kwargs):
        company = self.get_company()
        import_session = self.get_import_session(company)

        if import_session.status != "VALIDATED":
            return Response(
                {"detail": "Import session must be validated before commit."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        result = commit_import_rows(import_session)

        return Response(result, status=status.HTTP_200_OK)
    
    
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