from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import get_user_model
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from .models import Company

User = get_user_model()

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [ 
            "company_id",
            "name",
            "country",
            "industry",
            "organisation_email",
            "organisation_phone_number",
            "company_size",
            "company_type",
            "company_logo",
            "created_at",
            "owner"
            ]
        read_only_fields = ["company_id", "owner", "created_at"]


class MyOrganisationSerializer(serializers.ModelSerializer):
    membersCount = serializers.SerializerMethodField()
    assetsCount = serializers.SerializerMethodField()
    class Meta:
        model = Company
        fields = [
            "company_id",
            "name",
            "industry",
            "company_size",
            "country",
            "created_at",
            "company_logo",
            "membersCount",
            "assetsCount",
        ]
        read_only_fields = ["company_id"]

    def get_membersCount(self, obj):
            return obj.members.filter(is_active=True).count()
        
    def get_assetsCount(self, obj):
            return obj.assets.count()