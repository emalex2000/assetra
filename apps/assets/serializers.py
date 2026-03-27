from rest_framework import serializers
from .models import Asset, AssetCategories

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


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategories
        fields = "__all__"