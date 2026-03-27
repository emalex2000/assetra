from django.urls import path
from .views import CreateAssetView, CreateCategoryView
urlpatterns = [
    path('create_asset', CreateAssetView.as_view(), name='create-asset'),
    path('create_category', CreateCategoryView.as_view(), name='create-category'),
]