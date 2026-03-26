import random
from django.core.mail import send_mail
from django.conf import settings
import secrets


def generate_otp():
    return str(secrets.randbelow(900000) + 100000)

def send_otp_email(email, otp):
    send_mail(
        "your otp code ",
        f"your otp code is {otp} it expires in 5 minutes",
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )