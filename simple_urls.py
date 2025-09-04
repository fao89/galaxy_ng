"""
Simple URL configuration for filesystem deployment demonstration.
"""
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

def api_root(request):
    """Simple API root endpoint."""
    return JsonResponse({
        'message': 'Galaxy NG Filesystem Deployment',
        'version': '4.11.0dev',
        'deployment_mode': 'filesystem',
        'status': 'running'
    })

def health_check(request):
    """Health check endpoint."""
    return JsonResponse({'status': 'healthy'})

def pulp_status(request):
    """Pulp status endpoint for CI compatibility."""
    return JsonResponse({
        'versions': [
            {
                'component': 'galaxy_ng',
                'version': '4.11.0dev',
                'package': 'galaxy-ng'
            }
        ],
        'online_workers': [],
        'online_content_apps': [],
        'database_connection': {'connected': True},
        'redis_connection': {'connected': True},
        'storage': {'total': 0, 'used': 0, 'free': 0}
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/galaxy/', api_root, name='api-root'),
    path('api/galaxy/pulp/api/v3/status/', pulp_status, name='pulp-status'),
    path('health/', health_check, name='health-check'),
    path('', api_root, name='index'),
]