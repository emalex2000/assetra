from .utils import generate_otp, send_otp_email
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password
from .permissions import IsVerified, CanManageAsset
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .serializer import (
    CompanySerializer, 
    MyOrganisationSerializer, 
    JoinRequestListSerializer,
    JoinRequestReviewSerializer,
    OrganisationSearchResultSerializer,
    )
from django.db import transaction
from .models import OrganisationMember, Invite, Company, JoinRequest
from rest_framework.exceptions import PermissionDenied
from datetime import timedelta
from django.utils import timezone
import hashlib
from rest_framework import generics, status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404


User = get_user_model()

def normalize_email(email:str) -> str:
    return email.strip().lower()


@method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
class RegisterView(APIView):
    permission_classes = []
    def post(self, request):
        email = normalize_email(request.data.get("email", ""))
        phone_number = request.data.get("phone_number")
        password = request.data.get("password")

        if not email or not phone_number or not password:
            return Response({"error":"All Fields required"}, status=400)
        
        if User.objects.filter(email=email).exists():
            return Response({"error":"Email already exist"}, status=400)

        if User.objects.filter(phone_number=phone_number).exists():
            return Response({"error":"Phone number already exists"}, status=400)
        
        try:
            validate_password(password)
        except Exception as e:
            return Response({"error":list(e.messages)}, status=400)
        
        with transaction.atomic():
            #create user
            user = User.objects.create_user(
                email=email,
                password=password,
                phone_number=phone_number,
                is_valid=False,
        )
            otp = generate_otp()
            
            hashed_otp = hashlib.sha256(otp.encode()).hexdigest()

            cache.set(f"otp_{email}", hashed_otp, timeout=300) # 5mins
            cache.set(f"otp_attempts_{email}", 0, timeout=300)
            send_otp_email(email, otp)

        return Response({'message': f'otp sent to {email} '}, status=201)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response( 
                {"message": "logout successful"}, 
                status=status.HTTP_200_OK
                )
        except TokenError:
            return Response(
                {"error":"invalid or expired refresh token"}, 
                status=status.HTTP_400_BAD_REQUEST
                )


@method_decorator(ratelimit(key='ip', rate='3/m', block=True), name='dispatch')
class ResendOtpView(APIView):
    permission_classes = []

    def post(self, request):
        email = normalize_email(request.data.get("email", ""))
        last_sent = cache.get(f"otp_last_sent_{email}")

        if last_sent:
            return Response({"error" : "wait 60 seconds before requesting another code"}, status=429)
        
        otp = generate_otp()
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        cache.set(f"otp_{email}", hashed_otp, timeout=300)
        cache.set(f"otp_attempts_{email}", 0, timeout=300)
        cache.set(f"otp_last_sent_{email}", True, timeout=60)

        send_otp_email(email, otp)
        return Response({'Message': 'Otp sent successfully'}, status=200)

        
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsVerified])
def current_user(request):

    user = request.user
    memberships = OrganisationMember.objects.filter(
        user=user,
        is_active=True,
        company__isnull=False,
    ).select_related("company")

    roles = []
    for membership in memberships:
        roles.append({
            "company_id": str(membership.company.company_id),
            "company_name": membership.company.name,
            "role": membership.role,
        })

    profile_image_url = None
    if user.profile_image:
        try:
            profile_image_url = request.build_absolute_uri(user.profile_image.url)
        except ValueError:
            profile_image_url = None
        
    return Response(
        {
            'id': str(user.id),
            'email':user.email,
            'phone_number': str(user.phone_number) if user.phone_number else "",
            "profile_image": profile_image_url,
            'roles': roles,
        })


@method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='dispatch')
class VerifyOtpView(APIView):
    permission_classes = []
    def post(self, request):
        email = normalize_email(request.data.get("email", ""))
        otp = request.data.get("otp")

        otp_stored = cache.get(f"otp_{email}")
        attempts = cache.get(f"otp_attempts_{email}", 0)
        hashed_otp = hashlib.sha256(otp.encode()).hexdigest()
        if not otp_stored:
            return Response({'error': 'otp expired or not found'}, status=400)
        
        if attempts >= 5:
            return Response({'error': 'Maximum attempts exceeded'}, status=403)
        
        if hashed_otp != otp_stored:
            cache.set(f'otp_attempts_{email}', attempts + 1, timeout=300)
            return Response({"error": f"Invalid otp, {5 - (attempts +1)} attempts left"}, status=400)
        
        # else if your otp was a success
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error' : f'user with email {email} does not exist'}, status=404)
        user.is_valid = True
        user.save()

        # clear cache
        cache.delete(f'otp_{email}')
        cache.delete(f'otp_attempts_{email}')
        cache.delete(f"otp_last_sent_{email}")

        return Response({'Message' : 'Account verified successfully'}, status=200)
    
class CreateOrganisationView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request):
        data = request.data.copy()

        if not data.get("organisation_email"):
            data["organisation_email"] = request.user.email
        

        if not data.get("organisation_phone_number"):
            data["organisation_phone_number"] = request.user.phone_number

        serializer = CompanySerializer(data=data)
        if serializer.is_valid():
            company = serializer.save(owner=request.user)

            # attach user to company
            OrganisationMember.objects.create(
                user = request.user,
                company = company,
                role = "ADMIN", # fisrt user becomes admin
            )
            

            return Response({
                "message": "Company created succesfully", 
                "company": CompanySerializer(company).data,
                }, status=201)
        return Response(serializer.errors, status=400)
            

class CreateInviteview(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def post(self, request):
        email = request.data.get("email")
        role = request.data.get("role")

        if role not in ["STAFF", "RECIPIENT"]:
            return Response({"error": "invalid"}, status=400)
        
        membership = OrganisationMember.objects.filter(
            user=request.user,
            is_active=True
        ).first()

        if not membership or membership.role not in ["ADMIN", "STAFF"]:
            raise PermissionDenied("Action not allowed")
        
        invite = Invite.objects.create(
            company=membership.company,
            email=email,
            role=role,
            expires_at=timezone.now()+timedelta(days=2)
        )

        return Response({
            "message": "Invited Created Successfully",
            "email": invite.email,
            "token": str(invite.token),
            "role": invite.role,
            "expires_at": invite.expires_at,
        }, status=201)
    

class MyOrganisationsView(generics.ListAPIView):
    serializer_class = MyOrganisationSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        return Company.objects.filter(
            members__user=self.request.user,
            members__is_active=True,
        ).distinct()
    


class OrganisationSearchView(generics.ListAPIView):
    serializer_class = OrganisationSearchResultSerializer
    permission_classes = [IsAuthenticated, IsVerified]

    def get_queryset(self):
        query = self.request.query_params.get("q", "").strip()
        queryset = Company.objects.filter(is_listed=True)

        if query:
            queryset = queryset.filter(name__icontains=query)

        return queryset.order_by("name")


class CreateJoinRequestView(APIView):
    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request, company_id):
        company = get_object_or_404(Company, company_id=company_id)
        existing_membership = OrganisationMember.objects.filter(
            user=request.user,
            company=company,
            is_active=True,
        ).exists()

        if existing_membership:
            return Response(
                {"error": "you are already a member of this organisation"},status=400)
        
        existing_request = JoinRequest.objects.filter(
            user=request.user,
            company=company,
            status="PENDING",
        ).exists()

        if existing_request:
            return Response({"error": "you already have a pending request"}, status=400)
        
        if not company.allow_join_request:
            return Response(
                {"error":" this company does not allow join request"}, status=403
            )
        join_request = JoinRequest.objects.create(
            user=request.user,
            company=company,
            status="PENDING",
        )
        return Response(
            {
                "message": "join request sent successfully",
                "request": JoinRequestListSerializer(join_request).data,
                }, status=201)
    

class OrganisationJoinRequestListView(generics.ListAPIView):
    serializer_class = JoinRequestListSerializer
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def get_queryset(self):
        company_id = self.kwargs.get("organisationId")
        return JoinRequest.objects.filter(
            company_id=company_id,
            status="PENDING",
        ).select_related("user", "company").order_by("-created_at")
    

class ReviewJoinRequestView(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanManageAsset]

    def post(self, request, organisationId, request_id):
        company = get_object_or_404(Company, company_id=organisationId)
        join_request = get_object_or_404(JoinRequest, request_id=request_id, company=company, status="PENDING")

        serializer = JoinRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        action = serializer.validated_data["action"]

        if action == "APPROVED":
            membership_exists = OrganisationMember.objects.filter(
                user=join_request.user,
                company=company,
            ).exists()

            if not membership_exists:
                OrganisationMember.objects.create(
                    user=join_request.user,
                    company=company,
                    role="RECIPIENT",
                    is_active=True
                )
            join_request.status = "APPROVED"

        elif action=="REJECTED":
            join_request.status = "REJECTED"
        join_request.reviewed_by = request.user
        join_request.reviewed_at = timezone.now()
        join_request.save()
            
        return Response({
            "message": f"join request {join_request.status.lower()} successfully",
            "request": JoinRequestListSerializer(join_request).data
            }, status=200,)
        
        

        