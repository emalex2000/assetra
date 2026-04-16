from dj_rest_auth.registration.serializers import RegisterSerializer
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import CustomUser
from django.contrib.auth import get_user_model
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from .models import Company, JoinRequest

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
    

class OrganisationSearchSerializer(serializers.ModelSerializer):
     class Meta:
          model = Company
          fields = [
               "company_id",
               "name",
               "country",
               "industry",
          ]

    
class JoinRequestSerializer(serializers.ModelSerializer):
     class Meta:
          model = JoinRequest
          fields = ["request_id"]
          read_only_fields = ["request_id"]


class JoinRequestListSerializer(serializers.ModelSerializer):
     user_id = serializers.UUIDField(source="user.id", read_only=True)
     email = serializers.EmailField(source="user.email", read_only=True)
     phone_number = serializers.CharField(source="user.phone_number", read_only=True)

     class Meta:
        model = JoinRequest
        fields = [
            "request_id",
            "user_id",
            "email",
            "phone_number",
            "status",
            "created_at",
        ]


class JoinRequestReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approved", "reject"])
     