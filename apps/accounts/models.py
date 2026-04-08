from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from datetime import timedelta

ROLE_CHOICES = [
    ("ADMIN", "Admin"),
    ("STAFF","Staff"),
    ("RECIPIENT", "Recipient"),
]

def invite_expiry():
    return timezone.now() + timedelta(days=2)

def user_profile_upload_path(instance, filename):
    return f"users/{instance.id}/profile/{filename}"

def company_logo_upload_path(instance, filename):
    return f"companies/{instance.company_id}/logo/{filename}"
    

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("email required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)
    profile_image = models.ImageField(upload_to="users/profile_images/", null=True, blank=True)

    is_active = models.BooleanField(default=True) 
    is_staff = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    username = None

    def __str__(self):
        return self.email
    

class Company(models.Model):
    company_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    country = CountryField()
    industry = models.CharField(max_length=250, null=True, blank=True)
    organisation_email = models.EmailField(null=True, blank=True)
    organisation_phone_number = PhoneNumberField(null=True, blank=True)
    company_size = models.IntegerField(null=True, blank=True)
    company_type = models.CharField(max_length=30, null=True, blank=True)
    company_logo = models.ImageField(upload_to=company_logo_upload_path, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, related_name="owned_companies")
    
    def __str__(self):
        return self.name
    

class OrganisationMember(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="membership")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="members", null=True, blank=True)
    role = models.CharField(max_length=200, choices=ROLE_CHOICES, default="ADMIN")
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["user", "company"]


class Invite(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    token = models.UUIDField(default=uuid.uuid4, unique=True)

    expires_at = models.DateTimeField(default=invite_expiry)
    accepted = models.BooleanField(default=False)
