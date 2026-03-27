from django.db import models
from apps.accounts.models import Company, CustomUser
from simple_history.models import HistoricalRecords
from django_countries.fields import CountryField
import uuid

STATUS_CHOICES = [
    ("AVAILABLE", "Available"),
    ("ASSIGNED", "Assigned"),
    ("MAINTENANCE", "Maintenance"),
    ("RETIRED", "Retired"),
]

CONDITION_CHOICES = [
    ("NEW", "New"),
    ("GOOD", "Good"),
    ("DAMAGED", "Damaged"),
    ("REPAIRED", "Repaired"),
]

ASSIGNMENT_STATUS = [
    ("ACTIVE", "Active"),
    ('RETURNED', "Returned"),
    ("TRANSFERRED", "Transferred"),
    ("OVERDUE", "Overdue"),
]
class AssetCategories(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL)

    def __str__(self):
        return self.name
    
    
class Asset(models.Model):
    asset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, null=True)
    serial_number = models.CharField(max_length=250, unique=True, null=True)
    model = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="GOOD")
    category = models.ForeignKey(AssetCategories, on_delete=models.SET_NULL, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets")
    created_at = models.DateTimeField(auto_now_add=True)
    current_holder = models.ForeignKey(CustomUser, null=True, on_delete=models.SET_NULL, blank=True, related_name="held_assets")
    location_country = CountryField(blank=True)
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.name} - {self.serial_number}"
    

class AssetAssignment(models.Model):
    assignment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="asset_assignments")
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="assignment_asset")
    date_assigned = models.DateField(null=True, blank=True)
    received = models.BooleanField(default=False)
    location_country = CountryField()
    status = models.CharField(max_length=30, choices=ASSIGNMENT_STATUS, default="ACTIVE")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.asset} -> {self.user}"


class AssetTransfer(models.Model):
    transfer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="transfers")
    from_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="transfer_sent")
    to_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name="transfer_received")
    location_country = CountryField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.asset} {self.from_user} -> {self.to_user}"