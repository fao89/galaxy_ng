"""
Performance optimization settings for Galaxy NG.

This file contains Django settings specifically focused on improving
application performance through caching, database optimization,
and monitoring.
"""

import os

# Database Connection Optimization
DATABASES = {
    'default': {
        'OPTIONS': {
            'MAX_CONNS': 20,
            'OPTIONS': {
                'MAX_CONNS': 20,
                # Enable connection pooling
                'CONN_MAX_AGE': 600,  # 10 minutes
                # Optimize PostgreSQL specific settings
                'AUTOCOMMIT': True,
            }
        },
        'dynaconf_merge': True,
    }
}

# Enhanced Caching Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 20,
                'retry_on_timeout': True,
            },
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,
        },
        'KEY_PREFIX': 'galaxy_ng',
        'TIMEOUT': 300,  # 5 minutes default
        'VERSION': 1,
    },
    'sessions': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'galaxy_sessions',
        'TIMEOUT': 3600,  # 1 hour for sessions
    },
    'dynaconf_merge': True,
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'sessions'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False

# Template Caching
TEMPLATES = [{
    'OPTIONS': {
        'loaders': [
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]),
        ],
        'dynaconf_merge': True,
    },
    'dynaconf_merge': True,
}]

# Middleware Optimization
MIDDLEWARE = [
    # Add cache middleware at the top
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # Enable compression
] + [
    # Existing middleware will be merged
    'django.middleware.cache.FetchFromCacheMiddleware',
    'dynaconf_merge_unique',
]

# Cache Configuration
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300  # 5 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'galaxy_page'

# Static Files Optimization
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Database Query Optimization
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,  # Disable in production
}

# Logging Configuration for Performance Monitoring
LOGGING = {
    'loggers': {
        'galaxy_ng.performance': {
            'level': 'INFO',
            'handlers': ['performance'],
            'propagate': False,
        },
        'django.db.backends': {
            'level': 'WARNING',  # Reduce DB query logging in production
            'handlers': ['console'],
            'propagate': False,
        },
    },
    'handlers': {
        'performance': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'dynaconf_merge': True,
}

# Performance Specific Settings
GALAXY_PERFORMANCE_SETTINGS = {
    # Enable query optimization
    'ENABLE_QUERY_OPTIMIZATION': True,

    # Cache timeouts
    'NAMESPACE_CACHE_TIMEOUT': 3600,  # 1 hour
    'COLLECTION_CACHE_TIMEOUT': 300,  # 5 minutes
    'USER_CACHE_TIMEOUT': 600,       # 10 minutes
    'TASK_CACHE_TIMEOUT': 60,        # 1 minute

    # Database optimization
    'ENABLE_SELECT_RELATED': True,
    'ENABLE_PREFETCH_RELATED': True,
    'MAX_QUERY_LIMIT': 1000,

    # Async task optimization
    'TASK_BATCH_SIZE': 10,
    'TASK_RETRY_DELAY': 5,

    # Test optimization
    'FAST_TEST_MODE': os.getenv('FAST_TEST_MODE', False),
    'TEST_POLL_INTERVAL': 0.1,  # Faster polling in tests

    # Monitoring
    'ENABLE_PERFORMANCE_METRICS': True,
    'METRICS_COLLECTION_INTERVAL': 60,  # 1 minute
}

# Development vs Production Optimizations
if os.getenv('GALAXY_ENVIRONMENT') == 'production':
    # Production-specific optimizations
    GALAXY_PERFORMANCE_SETTINGS.update({
        'ENABLE_DEBUG_TOOLBAR': False,
        'LOG_LEVEL': 'WARNING',
        'CACHE_DEFAULT_TIMEOUT': 600,  # Longer cache times
    })
else:
    # Development-specific settings
    GALAXY_PERFORMANCE_SETTINGS.update({
        'ENABLE_DEBUG_TOOLBAR': True,
        'LOG_LEVEL': 'DEBUG',
        'CACHE_DEFAULT_TIMEOUT': 60,   # Shorter cache times for dev
    })

# Redis Cache Backend Settings (if using Redis)
if 'redis' in CACHES['default']['BACKEND'].lower():
    GALAXY_PERFORMANCE_SETTINGS.update({
        'REDIS_CACHE_ENABLED': True,
        'REDIS_CONNECTION_POOL_SIZE': 20,
        'REDIS_KEY_PREFIX': 'galaxy_ng:',
    })

# API Rate Limiting (if django-ratelimit is installed)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Content Delivery Optimization
USE_ETAGS = True
USE_L10N = True
USE_TZ = True

# File Upload Optimization
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Security with Performance Considerations
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Enable compression
USE_GZIP = True

# Performance Monitoring Integration Points
PERFORMANCE_MONITORING = {
    'PROMETHEUS_ENABLED': True,
    'METRICS_ENDPOINT': '/metrics',
    'HEALTH_CHECK_ENDPOINT': '/health',
    'SLOW_QUERY_THRESHOLD': 1.0,  # Log queries slower than 1 second
}

# Custom performance middleware configuration
GALAXY_CUSTOM_MIDDLEWARE = [
    'galaxy_ng.app.middleware.PerformanceMonitoringMiddleware',
    'galaxy_ng.app.middleware.CacheOptimizationMiddleware',
]
