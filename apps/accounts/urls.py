from django.urls import path
from .views import (
    RegisterView,
    VerifyOtpView, 
    current_user, 
    ResendOtpView, 
    CreateOrganisationView,
    MyOrganisationsView,
    OrganisationSearchView,
    CreateJoinRequestView,
    OrganisationJoinRequestListView,
    ReviewJoinRequestView,
    LogoutView,
    )

urlpatterns = [
    path('auth/user/', current_user, name='current_user'),
    path('signup/', RegisterView.as_view(), name='signup'),
    path('logout', LogoutView.as_view(), name='signout'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend_otp'),
    path('create-company/', CreateOrganisationView.as_view(), name='add_company'),
    path('my-organisations/', MyOrganisationsView.as_view(), name='my_organisations'),
    path('organisation_search/', OrganisationSearchView.as_view(), name='organisation-search'),
    path('organisations_search', OrganisationSearchView.as_view(), name='organisation-search'),
    #used company_id for uuid because its not under CanManageAsset permission
    path('organisation/<uuid:company_id>/join', CreateJoinRequestView.as_view(), name='join-request'),
    path('organisation/<uuid:organisationId>/join-requests/', OrganisationJoinRequestListView.as_view(), name='join_requests'),
    path('organisation/<uuid:organisationId>/join-requests/<uuid:request_id>/review', ReviewJoinRequestView.as_view(), name='review')
]