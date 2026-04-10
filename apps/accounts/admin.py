from django.contrib import admin
from .models import Company, OrganisationMember, CustomUser

admin.site.register(Company)
admin.site.register(OrganisationMember)
admin.site.register(CustomUser)
# Register your models here.
