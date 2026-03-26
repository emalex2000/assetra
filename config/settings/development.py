from .base import *


DEBUG = config("DJANGO_DEBUG")



DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'asset_tracker',
        'USER': 'postgres',
        'PASSWORD': config('DEV_DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5433',
    }
}
CACHES = {
    "default":{
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        # "LOCATION": "ratelimit_cache_table",
    }
}
CORS_ALLOW_ALL_ORIGIN = True