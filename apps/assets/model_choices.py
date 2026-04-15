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

IMPORT_STATUS = [
    ("UPLOADED", "Uploaded"),
    ("MAPPED", "Mapped"),
    ("VALIDATED", "Validated"),
    ("COMPLETED", "Completed"),
    ("FAILED", "Failed"),
]
