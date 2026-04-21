from django.urls import path
from .views import (
    CreateAssetView, 
    AssetCategoryListCreateView, 
    AssetListView, 
    AssetImportUploadView,
    AssetImportMappingView,
    AssetImportValidationView,
    AssetImportCommitView,
    CreateAssetAssigmentView,
    AssignableUsersView,
    AssetTransferView,
    AssignableAssetsView,
    AssetReceivedView,
    )

urlpatterns = [
    path('<uuid:organisationId>/create_asset/', CreateAssetView.as_view(), name='create-asset'),
    path('<uuid:organisationId>/assets/', AssetListView.as_view(), name='asset-list'),
    path('<uuid:organisationId>/categories/', AssetCategoryListCreateView.as_view(), name='create-category'),
    
    path('<uuid:organisationId>/assigments/create/', CreateAssetAssigmentView.as_view(), name="create_assignment"),
    path('<uuid:organisationId>/assignments/transfer/', AssetTransferView.as_view(), name='transfer'),
    path('<uuid:organisationId>/assignable-users', AssignableUsersView.as_view(), name='assignable_users'),
    path('<uuid:organisationId>/assignable-assets/', AssignableAssetsView.as_view(), name='assignable_assets'),
    path('assignments/received', AssetReceivedView.as_view(), name='asset_received'),

    path('<uuid:organisationId>/imports/upload/', AssetImportUploadView.as_view(), name='upload'),
    path('<uuid:organisationId>/imports/<uuid:importId>/map/', AssetImportMappingView.as_view(), name='import_mapping'),
    path('<uuid:organisationId>/imports/<uuid:importId>/validate/', AssetImportValidationView.as_view(), name='import_validation'),
    path('<uuid:organisationId>/imports/<uuid:importId>/commit/', AssetImportCommitView.as_view(), name='commit'),
]