from django.urls import path

from .views import RegisterView, VerifyOtpView, current_user, ResendOtpView


urlpatterns = [
    path('auth/user/', current_user, name='current_user'),
    path('signup/', RegisterView.as_view(), name='signup'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('resend-otp', ResendOtpView.as_view, name='resend_otp')
]