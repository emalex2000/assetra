from .models import Asset, AssetAssignment, AssetCategories, AssetImportSession
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsVerified, CanManageAsset
from rest_framework.response import Response
from .serializers import (
    AssetAssignmentListSerializer,
    AssetReceivedSerializer,
    AssetSerializer, 
    AssetCategorySerializer, 
    AssetAssignmentCreateSerializer, 
    AssetListSerializer, 
    AssetImportUploadSerializer,
    AssetImportMappingSerializer,
    AssignableUserSerializer,
    AssignableAssetSerializer,
    AssetTransferSerializer,
)
from datetime import date
from rest_framework.generics import CreateAPIView, ListCreateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied, NotFound
from apps.accounts.models import Company, OrganisationMember 
from .import_parser import extract_excel_metadata
from apps.assets.services.import_mappings import build_normalized_rows
from apps.assets.services.import_validation import validate_import_rows
from apps.assets.services.import_commit import commit_import_rows
from rest_framework import status
from django.db import transaction
from django.db.models import Q
from .models import AssetImportColumnMapping, AssetImportRow, AssetTransfer
from rest_framework.pagination import PageNumberPagination
from .tasks import commit_asset_import_task

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
        
        task = commit_asset_import_task.delay(str(import_session.import_id))

        return Response({
            "import_id": str(import_session.import_id),
            "task_id": task.id,
            "status": "QUEUED",
            "detail": "asset import has been queued for processing",
        })
    
    
class CreateAssetAssigmentView(CreateAPIView):
    serializer_class = AssetAssignmentCreateSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")
        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("the company does not exist")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True
        ).exists()

        if not is_member:
            raise PermissionDenied("you do not have permission to assign items in this organisation")

        return company


    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = self.get_company()
        return context

    
    @transaction.atomic
    def perform_create(self, serializer):
        asset = serializer.validated_data.get("asset")
        assignee = serializer.validated_data.get("user")

        assignment = serializer.save(assigned_by=self.request.user, status="ACTIVE", received=False)
        asset.status = "ASSIGNED"
        asset.current_holder = assignee
        asset.location_country = assignment.location_country
        asset.save(update_fields=["status", "current_holder", "location_country"])


class AssignableUsersView(ListAPIView):
    serializer_class = AssignableUserSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("organisation does not exist")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
            role__in=["ADMIN", "STAFF"]
        ).exists()

        if not is_member:
            raise PermissionDenied("you do not have permission to view assignable users")

        return company


    def get_queryset(self):
        company=self.get_company()
        query = self.request.query_params.get("q", "").strip()

        queryset = OrganisationMember.objects.filter(
            company=company,
            is_active=True,
            user__is_active=True,
        ).select_related("user").order_by("user__email")

        if query:
            queryset = queryset.filter(
                Q(user__email__icontains=query) |
                Q(user__phone_number__icontains=query) |
                Q(role__icontains=query)
            )

        return queryset


class AssignableAssetsView(ListAPIView):
    serializer_class = AssignableAssetSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("company does not exist")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
            role__in=["ADMIN", "STAFF"]
        ).exists()

        if not is_member:
            raise PermissionDenied("you do not have permission to view these assets")

        return company

    def get_queryset(self):
        company = self.get_company()
        query = self.request.query_params.get("q", "").strip()
        include_assigned = self.request.query_params.get("include_assigned", "false").lower() == "true"

        queryset = Asset.objects.filter(company=company).select_related(
            "category", "current_holder"
        ).order_by("name")

        if not include_assigned:
            queryset = queryset.filter(status="AVAILABLE", current_holder__isnull=True,)

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(serial_number__icontains=query) |
                Q(model__icontains=query) |
                Q(category__name__icontains=query) 
            )

        return queryset


class AssetTransferView(APIView):
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
            role__in=["ADMIN", "STAFF"],
        ).exists()

        if not is_member:
            raise PermissionDenied("You do not have permission to transfer assets in this organisation.")

        return company

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        company = self.get_company()
        serializer = AssetTransferSerializer(
            data=request.data,
            context={"company": company}
        )
        serializer.is_valid(raise_exception=True)

        asset = serializer.validated_data["asset_obj"]
        to_user = serializer.validated_data["to_user_obj"]
        active_assignment = serializer.validated_data["active_assignment"]
        location_country = serializer.validated_data["location_country"]
        notes = serializer.validated_data.get("notes", "")

        from_user = active_assignment.user

        active_assignment.status = "TRANSFERRED"
        active_assignment.save(update_fields=["status"])

        transfer = AssetTransfer.objects.create(
            asset=asset,
            from_user=from_user,
            to_user=to_user,
            location_country=location_country,
            created_by=request.user,
        )

        new_assignment = AssetAssignment.objects.create(
            asset=asset,
            user=to_user,
            assigned_by=request.user,
            date_assigned=date.today(),
            location_country=location_country,
            status="ACTIVE",
            received=False,
            notes=notes,
        )

        asset.current_holder = to_user
        asset.status = "ASSIGNED"
        asset.location_country = location_country
        asset.save(update_fields=["current_holder", "status", "location_country"])

        return Response(
            {
                "detail": "Asset transferred successfully.",
                "transfer_id": str(transfer.transfer_id),
                "assignment_id": str(new_assignment.assignment_id),
                "pending_receive": True,
            },
            status=status.HTTP_201_CREATED,
        )


class AssetReceivedView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = AssetReceivedSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment_id = serializer.validated_data["assignment_id"]

        try:
            assignment = AssetAssignment.objects.select_related("asset", "user").get(
                assignment_id=assignment_id,
                user=request.user,
                status="ACTIVE"
            )

        except assignment.DoesNotExist:
            raise NotFound("active assignment not found for this user")

        if assignment.received:
            return Response(
                {"detail":"asset already marked as received"}, status=400
            )

        assignment.received = True
        assignment.save(update_fields=["received"])
        return Response({
            "detail": "asset marked as received",
            "assignment_id": str(assignment.assignment_id),
            "asset_id": str(assignment.asset.asset_id),
            "received": True
        }, status=200)
    

class AssetAssignmentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50


class OrganisationAssignmentListView(ListAPIView):
    serializer_class = AssetAssignmentListSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]
    pagination_class = AssetAssignmentPagination

    def get_company(self):
        organisation_id = self.kwargs.get("organisationId")

        try:
            company = Company.objects.get(company_id=organisation_id)
        except Company.DoesNotExist:
            raise NotFound("company does not exist")

        is_member = OrganisationMember.objects.filter(
            user=self.request.user,
            company=company,
            is_active=True,
            role__in=["ADMIN", "STAFF"]
        ).exists()

        if not is_member:
            raise PermissionDenied("you do not have permission to view assignments")

        return company

    def get_queryset(self):
        company = self.get_company()
        query = self.request.query_params.get("q", "").strip()
        status_param = self.request.query_params.get("status", "").strip()
        received_param = self.request.query_params.get("received", "").strip().lower()

        queryset = (
            AssetAssignment.objects.filter(asset__company=company)
            .select_related("asset", "user")
            .order_by("-assignment_id")
        )

        if query:
            queryset = queryset.filter(
                Q(asset__name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(location_country__icontains=query)
            )

        if status_param:
            queryset = queryset.filter(status=status_param)

        if received_param in ["true", "false"]:
            queryset = queryset.filter(received=(received_param == "true"))

        return queryset