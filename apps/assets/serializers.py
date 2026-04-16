from rest_framework import serializers
from .models import Asset, AssetCategories, AssetAssignment
from .constants import SUPPORTED_IMPORT_FIELDS
from django_countries import countries


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
        

        
class AssetAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetAssignment
        fields = [
            "assignment_id", 
            "asset", 
            "user", 
            "assigned_by", 
            "date_assigned", 
            "location_country",
            "status",
            "notes",
            ]
        read_only_fields = ["assignment_id"]