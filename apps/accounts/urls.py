from django.urls import path
from .views import (
    RegisterView,
    VerifyOtpView, 
    current_user, 
    ResendOtpView, 
    CreateOrganisationView,
    MyOrganisationsView,
    LogoutView
    )

urlpatterns = [
    path('auth/user/', current_user, name='current_user'),
    path('signup/', RegisterView.as_view(), name='signup'),
    path('logout', LogoutView.as_view(), name='signout'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend_otp'),
    path('create-company/', CreateOrganisationView.as_view(), name='add_company'),
    path('my-organisations/', MyOrganisationsView.as_view(), name='my_organisations'),
]