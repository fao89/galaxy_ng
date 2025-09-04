"""
Minimal settings for database migrations only.
This file bypasses the complex dynaconf setup to allow migrations to run.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / ...
BASE_DIR = Path(__file__).absolute().parent

# Basic Django settings
DEBUG = True
SECRET_KEY = 'migration-key-only-not-for-production'
ALLOWED_HOSTS = ["*"]

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'galaxy_ng'),
        'USER': os.environ.get('POSTGRES_USER', 'galaxy_ng'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'galaxy_ng'),
        'HOST': os.environ.get('DATABASES__default__HOST', 'postgres'),
        'PORT': os.environ.get('DATABASES__default__PORT', '5432'),
        'CONN_MAX_AGE': 0,
    }
}

# Minimal installed apps for migrations (filesystem mode without pulpcore)
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'crum',
    'ansible_base.resource_registry',
    'ansible_base.rbac',
    'social_django',
    'flags',
    'ansible_base.feature_flags',
    'galaxy_ng.app_fs',
]

# Basic middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'crum.CurrentRequestUserMiddleware',
]

# Auth model
AUTH_USER_MODEL = 'galaxy_fs.User'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Filesystem deployment settings
DEPLOY_ROOT = Path("/var/lib/galaxy")
MEDIA_ROOT = str(DEPLOY_ROOT / "media")
STATIC_URL = "/static/"
STATIC_ROOT = DEPLOY_ROOT / STATIC_URL.strip("/")

# Galaxy content settings for filesystem mode
GALAXY_CONTENT_ROOT = "/content"
GALAXY_TASK_STORAGE = "/var/lib/galaxy/tasks"

# Cache settings
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Templates configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Other Django settings
USE_TZ = True
USE_I18N = True
USE_L10N = True
TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Feature flags
GALAXY_FEATURE_FLAGS = {
    'display_repositories': False,
    'execution_environments': False,
    'legacy_roles': False,
    'ai_deny_index': False,
    'dab_resource_registry': True,
    'external_authentication': False,
}

# Default org
DEFAULT_ORGANIZATION_NAME = "Default"

# Ansible base settings
ANSIBLE_BASE_RESOURCE_CONFIG_MODULE = "galaxy_ng.app_fs.api.resource_api"
ANSIBLE_BASE_ORGANIZATION_MODEL = "galaxy_fs.Organization"
ANSIBLE_BASE_TEAM_MODEL = "galaxy_fs.Team"

# Task system settings for filesystem mode
GALAXY_TASK_WORKERS = 4
GALAXY_TASK_POLL_INTERVAL = 5
GALAXY_TASK_RETENTION_DAYS = 30
GALAXY_WORKER_TIMEOUT_MINUTES = 5

# Validation settings
GALAXY_QUICK_VALIDATION = True
GALAXY_REQUIRE_CONTENT_APPROVAL = True

# Storage settings
FILE_UPLOAD_TEMP_DIR = "/tmp"
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB

# Authentication settings
GALAXY_AUTHENTICATION_CLASSES = [
    "galaxy_ng.app.auth.session.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication", 
    "rest_framework.authentication.BasicAuthentication",
]

# URL configuration
ROOT_URLCONF = 'simple_urls'

# API configuration  
GALAXY_API_PATH_PREFIX = "/api/galaxy/"
GALAXY_DEPLOYMENT_MODE = "standalone"
GALAXY_EXCEPTION_HANDLER = 'galaxy_ng.app.api.exceptions.exception_handler'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 20,
}

# DRF Spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'Galaxy NG API',
    'DESCRIPTION': 'Galaxy NG Filesystem API',
    'VERSION': '1.0.0',
}

# RBAC model registry for filesystem mode
ANSIBLE_BASE_RBAC_MODEL_REGISTRY = {
    'galaxy_fs.namespace': {'parent_field_name': None},
    'galaxy_fs.team': {'parent_field_name': 'organization'},
    'galaxy_fs.organization': {'parent_field_name': None},
    'galaxy_fs.collectionimport': {'parent_field_name': 'namespace'},
}

# Managed role registry
ANSIBLE_BASE_MANAGED_ROLE_REGISTRY = {
    'platform_auditor': {'name': 'Platform Auditor', 'shortname': 'sys_auditor'},
    'team_member': {},
    'team_admin': {},
    'org_admin': {},
    'org_member': {},
}