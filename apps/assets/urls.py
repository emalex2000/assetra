from django.urls import path
from .views import (
    CreateAssetView, 
    AssetCategoryListCreateView, 
    AssetListView, 
    AssetImportUploadView,
    AssetImportMappingView,
    AssetImportValidationView,
    AssetImportCommitView,
    )

urlpatterns = [
    path('<uuid:organisationId>/create_asset/', CreateAssetView.as_view(), name='create-asset'),
    path('<uuid:organisationId>/assets/', AssetListView.as_view(), name='asset-list'),
    path('<uuid:organisationId>/categories/', AssetCategoryListCreateView.as_view(), name='create-category'),
    path('<uuid:organisationId>/imports/upload/', AssetImportUploadView.as_view(), name='upload'),
    path('<uuid:organisationId>/imports/<uuid:importId>/map/', AssetImportMappingView.as_view(), name='import_mapping'),
    path('<uuid:organisationId>/imports/<uuid:importId>/validate/', AssetImportValidationView.as_view(), name='import_validation'),
    path('<uuid:organisationId>/imports/<uuid:importId>/commit/', AssetImportCommitView.as_view(), name='commit'),
]