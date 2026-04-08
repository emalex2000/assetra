from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import authenticate

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("email and password required")
        
        user = authenticate(
            request = self.context.get("request"),
            email=email, 
            password=password,
        )
        if user is None:
            raise serializers.ValidationError("invalid email or password")
        
        if not user.is_active:
            raise serializers.ValidationError("this account is inactive")
        
        if not user.is_valid:
            raise serializers.ValidationError("please verify your account first")
        
        refresh = self.get_token(user)
        return{
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": str(user.id),
                "email": user.email,
            }
        }
            