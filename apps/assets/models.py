from django.db import models
from apps.accounts.models import Company, CustomUser
from .model_choices import STATUS_CHOICES, CONDITION_CHOICES, ASSIGNMENT_STATUS, IMPORT_STATUS
from simple_history.models import HistoricalRecords
from django_countries.fields import CountryField
import uuid



class AssetCategories(models.Model):
    category_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, null=True)
    description = models.TextField(blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.name
    
    
class Asset(models.Model):
    asset_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, null=True)
    serial_number = models.CharField(max_length=250, null=True, blank=True)
    model = models.CharField(max_length=250, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="GOOD")
    category = models.ForeignKey(AssetCategories, on_delete=models.SET_NULL, null=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="assets")
    created_at = models.DateTimeField(auto_now_add=True)
    current_holder = models.ForeignKey(CustomUser, null=True, on_delete=models.SET_NULL, blank=True, related_name="held_assets")
    location_country = CountryField(blank=True)
    history = HistoricalRecords()
    
    class Meta:
        unique_together = ["serial_number", "company"]

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

    class Meta:
        unique_together = ["asset", "user"]

        
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


class AssetImportSession(models.Model):
    import_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="asset_imports")
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    original_file = models.FileField(upload_to="asset_imports/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=IMPORT_STATUS, default="UPLOADED")
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    invalid_rows = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AssetImportColumnMapping(models.Model):
    session = models.ForeignKey(AssetImportSession, on_delete=models.CASCADE, related_name="column_mappings")
    source_column = models.CharField(max_length=255)
    target_field = models.CharField(max_length=255, null=True, blank=True)
    is_skipped = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "source_column")


class AssetImportRow(models.Model):
    session = models.ForeignKey(AssetImportSession, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField(default=0)
    raw_data = models.JSONField(default=dict)
    normalized_data = models.JSONField(default=dict)
    is_valid = models.BooleanField(default=False)
    errors = models.JSONField(default=list)
    imported_assets = models.ForeignKey("assets.Asset", on_delete=models.SET_NULL, null=True, related_name="import_rows")

    class Meta:
        unique_together = ["session", "row_number"]
