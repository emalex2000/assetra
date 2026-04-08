from .utils import generate_otp, send_otp_email
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password
from .permissions import IsVerified, CanAssignAsset
from django.core.cache import cache
# from django_ratelimit.decorators import ratelimit
# from django.utils.decorators import method_decorator
from .serializer import CompanySerializer
from django.db import transaction
from .models import OrganisationMember, Invite
from rest_framework.exceptions import PermissionDenied
from datetime import timedelta
from django.utils import timezone
import hashlib


User = get_user_model()

def normalize_email(email:str) -> str:
    return email.strip().lower()



# @method_decorator(ratelimit(key='ip', rate='5/m', block=True), name='dispatch')
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

# @method_decorator(ratelimit(key='ip', rate='3/m', block=True), name='dispatch')
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
    return Response(
        {
            'id': request.user.id,
            'email': request.user.email,
        }
    )


# @method_decorator(ratelimit(key='ip', rate='10/m', block=True), name='dispatch')
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

        serializer = CompanySerializer(data=request.data)
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
                "company": serializer.data
                }, status=201)
        return Response(serializer.errors, status=400)
            

class CreateInviteview(APIView):
    permission_classes = [IsAuthenticated, IsVerified, CanAssignAsset]

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