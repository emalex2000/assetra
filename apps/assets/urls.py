from django.urls import path
from .views import CreateAssetView, AssetCategoryListCreateView
urlpatterns = [
    path('<uuid:organisationId>/create_asset/', CreateAssetView.as_view(), name='create-asset'),
    path('<uuid:organisationId>/categories/', AssetCategoryListCreateView.as_view(), name='create-category'),
]