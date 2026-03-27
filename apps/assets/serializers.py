from rest_framework import serializers
from .models import Asset, AssetCategories, AssetAssignment

class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            "asset_id",
            "name",
            "serial_number",
            "model",
            "status",
            "condition",
            "category",
            "location_country"
        ]
        read_only_fields = ["asset_id"]
        def validate_category(self, value):
            user = self.context["request"].user

            if value and value.company != user.company:
                raise serializers.ValidationError("invalid category for your company")
            return value


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategories
        fields = "__all__"
        read_only_fields = ["company"]


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