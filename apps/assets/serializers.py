from rest_framework import serializers
from .models import Asset, AssetCategories, AssetAssignment
from .constants import SUPPORTED_IMPORT_FIELDS
from django_countries import countries
from apps.accounts.models import OrganisationMember
from phonenumber_field.serializerfields import PhoneNumberField

def validate_location_country(self, value):
    # If already a valid code, return
    if value in dict(countries):
        return value

    # Try matching by name
    for code, name in countries:
        if name.lower() == str(value).lower():
            return code

    raise serializers.ValidationError("Invalid country")


class AssetSerializer(serializers.ModelSerializer):
    def validate_category(self, value):
        company = self.context.get("company")

        if value and value.company != company:
            raise serializers.ValidationError("invalid category of this organisation")
        return value

    class Meta:
        model = Asset
        fields = [
            "name",
            "serial_number",
            "model",
            "category",
            "location_country"
        ]
        read_only_fields = ["asset_id", "status", "asset_id", "condition",]


class AssetListSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="name", read_only=True)
    category_name = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()
    assignment_state = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "asset_id",
            "asset_name",
            "serial_number",
            "model",
            "assigned_to",
            "category_name",
            "status",
            "condition",
            "location_country",
            "assignment_state",
            ]
        
    def get_category_name(self, obj):
        return obj.category.name if obj.category else None
    
    def get_assigned_to(self, obj):
        assignment = (
            AssetAssignment.objects.filter(asset=obj, status="ACTIVE").select_related("user").first()
            )
        if not assignment or not assignment.user:
            return None
        
        return assignment.user.email

    def get_assignment_state(self, obj):
        assignment = (
            AssetAssignment.objects.filter(asset=obj, status="ACTIVE")
            .select_related("user")
            .first()
            )

        if not assignment:
            return "AVAILABLE"

        if not assignment.received:
            return "PENDING_RECEIVE"

        return "ASSIGNED"
        


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategories
        fields = "__all__"
        read_only_fields = ["company"]


class AssetImportUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    def validate_file(self, value):
        filename = value.name.lower()

        if not filename.endswith(".xlsx"):
            raise serializers.ValidationError("only .xslx files are allowed for now")
        
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("file must be less than 10mb.")
        
        return value


class AssetImportMappingSerializer(serializers.Serializer):
    mappings = serializers.DictField(
        child = serializers.CharField(allow_null=True, required=False),
        allow_empty = False,
    )

    def validate_mappings(self, value):
        valid_targets = set(SUPPORTED_IMPORT_FIELDS.keys())
        used_targets = set()

        for source_columns, target_fields in value.items():
            if target_fields in ("", None, "null"):
                continue
            
            if target_fields not in valid_targets:
                raise serializers.ValidationError(
                    f"{target_fields} is an unsupported import field"
                )
            
            if target_fields in used_targets:
                raise serializers.ValidationError(
                    f"{target_fields} cannot be mapped more than once"
                )
            
            used_targets.add(target_fields)
        return value 


class AssetAssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = [
            "assignment_id",
            "asset",
            "user",
            "date_assigned",
            "location_country",
            "notes",
        ]
        read_only_fields = ["assignment_id"]

        def validate_asset(self, value):
            company = self.context["company"]

            if value.company != company:
                raise serializers.ValidationError("this asset does not belong to this organisation")
            
            if value.status != "AVAILABLE":
                raise serializers.ValidationError("this asset is not available for assignment")

            if value.current_holder is not None:
                raise serializers.ValidationError("this asset already belongs to someone else")
            
            active_assignment_exists = AssetAssignment.objects.filter(
                status="ACTIVE",
                asset=value
            ).exists()

            if active_assignment_exists:
                raise serializers.ValidationError("an active assignment already exists with this assset")
            
            return value
        
        def validate_user(self, value):
            company = self.context["company"]
            is_member = OrganisationMember.objects.filter(
                company=company,
                user=value,
                is_active=True,
            ).exists()

            if not is_member:
                raise serializers.ValidationError("user is not an active member of this organisation")
            
            return value

        def validate(self, attrs):
            asset = attrs.get("asset")
            user = attrs.get("user")

            if asset and user and asset.current_holder == user:
                raise serializers.ValidationError("asset alread belong to this user")
            return attrs


class AssignableUserSerializer(serializers.ModelSerializer):
    user_id =serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    phone_number = PhoneNumberField(source="user.phone_number", read_only=True)
    role = serializers.CharField(read_only=True)
    joined_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = OrganisationMember
        fields = [
            "user_id",
            "email",
            "phone_number",
            "role",
            "joined_at",
        ]


class AssignableAssetSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source='name', read_only=True)
    category_name = serializers.SerializerMethodField()
    current_holder_email = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "asset_id",
            "asset_name",
            "serial_number",
            "model",
            "category_name",
            "status",
            "condition",
            "location_country",
            "current_holder_email",
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_current_holder_email(self, obj):
        return obj.current_holder.email if obj.current_holder else None


class AssetTransferSerializer(serializers.Serializer):
    asset = serializers.UUIDField()
    to_user = serializers.UUIDField()
    location_country = serializers.CharField()
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        company = self.context["company"]
        asset_id = attrs["asset"]
        to_user_id = attrs["to_user"]

        try:
            asset = Asset.objects.select_related("current_holder").get(
                asset_id=asset_id,
                company=company
            )
        except Asset.DoesNotExist:
            raise serializers.ValidationError({"asset": "Asset not found in this organisation."})

        if asset.current_holder is None:
            raise serializers.ValidationError({"asset": "Asset does not currently have a holder to transfer from."})

        try:
            new_user_membership = OrganisationMember.objects.select_related("user").get(
                user_id=to_user_id,
                company=company,
                is_active=True,
            )
        except OrganisationMember.DoesNotExist:
            raise serializers.ValidationError({"to_user": "Target user is not an active member of this organisation."})

        if str(asset.current_holder.id) == str(to_user_id):
            raise serializers.ValidationError({"to_user": "Asset is already assigned to this user."})

        active_assignment = AssetAssignment.objects.filter(
            asset=asset,
            status="ACTIVE",
        ).select_related("user").first()

        if not active_assignment:
            raise serializers.ValidationError({"asset": "No active assignment exists for this asset."})

        attrs["asset_obj"] = asset
        attrs["to_user_obj"] = new_user_membership.user
        attrs["active_assignment"] = active_assignment
        return attrs


class AssetReceivedSerializer(serializers.Serializer):
    assignment_id = serializers.UUIDField()