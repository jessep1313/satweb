"""
Configuración para entorno local.
Usa django-environ para leer .env
"""
from .base import *
import environ

env = environ.Env()
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')

DEBUG = env.bool('DEBUG', default=True)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Configuración de bases de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_DEFAULT_NAME'),
        'USER': env('DB_DEFAULT_USER'),
        'PASSWORD': env('DB_DEFAULT_PASSWORD'),
        'HOST': env('DB_DEFAULT_HOST'),
        'PORT': env('DB_DEFAULT_PORT'),
    },
    'empresa1': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_EMPRESA1_NAME'),
        'USER': env('DB_EMPRESA1_USER'),
        'PASSWORD': env('DB_EMPRESA1_PASSWORD'),
        'HOST': env('DB_EMPRESA1_HOST'),
        'PORT': env('DB_EMPRESA1_PORT'),
    },
    'empresa2': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_EMPRESA2_NAME'),
        'USER': env('DB_EMPRESA2_USER'),
        'PASSWORD': env('DB_EMPRESA2_PASSWORD'),
        'HOST': env('DB_EMPRESA2_HOST'),
        'PORT': env('DB_EMPRESA2_PORT'),
    },
    'empresa3': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_EMPRESA3_NAME'),
        'USER': env('DB_EMPRESA3_USER'),
        'PASSWORD': env('DB_EMPRESA3_PASSWORD'),
        'HOST': env('DB_EMPRESA3_HOST'),
        'PORT': env('DB_EMPRESA3_PORT'),
    },
    'empresa4': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_EMPRESA4_NAME'),
        'USER': env('DB_EMPRESA4_USER'),
        'PASSWORD': env('DB_EMPRESA4_PASSWORD'),
        'HOST': env('DB_EMPRESA4_HOST'),
        'PORT': env('DB_EMPRESA4_PORT'),
    },
    'empresa5': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_EMPRESA5_NAME'),
        'USER': env('DB_EMPRESA5_USER'),
        'PASSWORD': env('DB_EMPRESA5_PASSWORD'),
        'HOST': env('DB_EMPRESA5_HOST'),
        'PORT': env('DB_EMPRESA5_PORT'),
    },
}

# Rutina para que apunte al archivo local.py como configuración por defecto
# En manage.py y wsgi.py debemos cambiar el módulo de settings