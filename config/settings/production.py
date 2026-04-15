from .base import *


DEBUG = False


ALLOWED_HOSTS = ["yourdomain.com"]


tmpPostgres = urlparse(config("NEON_DB_URL"))

DATABASES = {
    'default': {
        # 'ENGINE': 'django.db.backends.postgresql',
        'ENGINE': 'django_db_geventpool.backends.postgresql_psycopg2',
        'NAME': tmpPostgres.path.replace('/', ''),
        'USER': tmpPostgres.username,
        'PASSWORD': tmpPostgres.password,
        'HOST': tmpPostgres.hostname,
        'PORT': 5432,
        'OPTIONS': dict(parse_qsl(tmpPostgres.query)),
        "CONN_MAX_AGE": 0,
        "ATOMIC_REQUESTS": False,
        "POOL_OPTIONS": {
            "MAX_CONNS": 20,
            "REUSE_CONNS": 10,
        }
    }
}

# CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
# CELERY_ACCEPT_CONTENT = ["json"]
# CELERY_TASK_SERIALIZER = "json"


