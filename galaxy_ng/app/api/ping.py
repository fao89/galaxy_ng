import os
from importlib.metadata import version, PackageNotFoundError

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from pulpcore.app.views import StatusView
from rest_framework import status
from rest_framework.response import Response

from galaxy_ng.app.api.utils import get_aap_version


def get_version_from_metadata(package_name):
    """Uses importlib.metadata.version to retrieve package version"""
    try:
        return version(package_name)
    except PackageNotFoundError:
        return ""


def get_galaxy_ng_versions():
    """Get version information for galaxy_ng and related packages"""
    versions = {
        "galaxy_ng_version": apps.get_app_config("galaxy").version,
        "galaxy_importer_version": get_version_from_metadata("galaxy-importer"),
        "pulpcore_version": apps.get_app_config('core').version,
        "pulp_ansible_version": apps.get_app_config('ansible').version,
        "pulp_container_version": apps.get_app_config('container').version,
        "ansible_base_version": get_version_from_metadata("django-ansible-base"),
        "ansible_lint_version": get_version_from_metadata("ansible-lint"),
        "dynaconf_version": get_version_from_metadata("dynaconf"),
        "django_version": get_version_from_metadata("django"),
    }

    if os.environ.get("GIT_COMMIT"):
        versions["galaxy_ng_commit"] = os.environ.get("GIT_COMMIT", "")

    # Add AAP version if available
    cached_aap_version = cache.get('aap_version')
    if cached_aap_version is None:
        aap_version = get_aap_version()
        if aap_version:
            cached_aap_version = aap_version
            cache.set('aap_version', aap_version)

    if cached_aap_version:
        versions["aap_version"] = cached_aap_version

    return versions


class BasePingView(StatusView):
    """
    Base ping endpoint that extends pulpcore's StatusView to check system health.
    """

    def get_status_data(self, request, *args, **kwargs):
        """Get the standard status response from parent StatusView"""
        response = super().get(request, *args, **kwargs)

        if response.status_code != status.HTTP_200_OK:
            return None, response

        return response.data, None

    def check_database(self, data, filter_func=None):
        """Check database connection"""
        if not data.get("database_connection", {}).get("connected", False):
            return self.create_database_error_response(data, filter_func)
        return None

    def check_redis(self, data, filter_func=None):
        """Check Redis connection"""
        if settings.CACHE_ENABLED and not data.get("redis_connection", {}).get("connected", False):
            return self.create_redis_error_response(data, filter_func)
        return None

    def create_service_unavailable_response(self, error_message, data):
        """Create a standardized HTTP 503 Service Unavailable response"""
        return Response(
            {"error": error_message, "data": data},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    def create_database_error_response(self, data, filter_func=None):
        """Create HTTP 503 response for database connection error"""
        filtered_data = filter_func(data) if filter_func else data
        return self.create_service_unavailable_response(
            "Database is not connected", filtered_data
        )

    def create_redis_error_response(self, data, filter_func=None):
        """Create HTTP 503 response for Redis connection error"""
        filtered_data = filter_func(data) if filter_func else data
        return self.create_service_unavailable_response(
            "Redis is not connected", filtered_data
        )

    def create_api_apps_error_response(self, data, filter_func=None):
        """Create HTTP 503 response for no API apps available"""
        filtered_data = filter_func(data) if filter_func else data
        return self.create_service_unavailable_response(
            "No online API apps available", filtered_data
        )

    def create_content_apps_error_response(self, data, filter_func=None):
        """Create HTTP 503 response for no content apps available"""
        filtered_data = filter_func(data) if filter_func else data
        return self.create_service_unavailable_response(
            "No online content apps available", filtered_data
        )

    def create_workers_error_response(self, data, filter_func=None):
        """Create HTTP 503 response for no workers available"""
        filtered_data = filter_func(data) if filter_func else data
        return self.create_service_unavailable_response(
            "No online workers available", filtered_data
        )

    def filter_api_data(self, data):
        """Filter data to only include API-related information"""
        return {
            "online_api_apps": data.get("online_api_apps"),
            "database_connection": data.get("database_connection"),
            "redis_connection": data.get("redis_connection"),
            "storage": data.get("storage"),
            "versions": get_galaxy_ng_versions(),
        }

    def filter_content_data(self, data):
        """Filter data to only include content-related information"""
        return {
            "online_content_apps": data.get("online_content_apps"),
            "database_connection": data.get("database_connection"),
            "redis_connection": data.get("redis_connection"),
            "storage": data.get("storage"),
            "content_settings": data.get("content_settings"),
            "versions": get_galaxy_ng_versions(),
        }

    def filter_worker_data(self, data):
        """Filter data to only include worker-related information"""
        return {
            "online_workers": data.get("online_workers"),
            "database_connection": data.get("database_connection"),
            "redis_connection": data.get("redis_connection"),
            "storage": data.get("storage"),
            "versions": get_galaxy_ng_versions(),
        }


class PingApiView(BasePingView):
    """
    API ping endpoint that validates API-related components.

    Returns error status when:
    - Database isn't connected
    - Redis isn't connected
    - online_api_apps == 0
    """

    def get(self, request, *args, **kwargs):
        data, error_response = self.get_status_data(request, *args, **kwargs)
        if error_response:
            return error_response

        # Check database connection
        db_error = self.check_database(data, self.filter_api_data)
        if db_error:
            return db_error

        # Check Redis connection
        redis_error = self.check_redis(data, self.filter_api_data)
        if redis_error:
            return redis_error

        # Check online API apps
        if data.get("online_api_apps", 0) == 0:
            return self.create_api_apps_error_response(data, self.filter_api_data)

        return Response(self.filter_api_data(data), status=status.HTTP_200_OK)


class PingContentView(BasePingView):
    """
    Content ping endpoint that validates content-related components.

    Returns error status when:
    - Database isn't connected
    - Redis isn't connected
    - online_content_apps == 0
    """

    def get(self, request, *args, **kwargs):
        data, error_response = self.get_status_data(request, *args, **kwargs)
        if error_response:
            return error_response

        # Check database connection
        db_error = self.check_database(data, self.filter_content_data)
        if db_error:
            return db_error

        # Check Redis connection
        redis_error = self.check_redis(data, self.filter_content_data)
        if redis_error:
            return redis_error

        # Check online content apps
        if data.get("online_content_apps", 0) == 0:
            return self.create_content_apps_error_response(data, self.filter_content_data)

        return Response(self.filter_content_data(data), status=status.HTTP_200_OK)


class PingWorkerView(BasePingView):
    """
    Worker ping endpoint that validates worker-related components.

    Returns error status when:
    - Database isn't connected
    - Redis isn't connected
    - online_workers == 0
    """

    def get(self, request, *args, **kwargs):
        data, error_response = self.get_status_data(request, *args, **kwargs)
        if error_response:
            return error_response

        # Check database connection
        db_error = self.check_database(data, self.filter_worker_data)
        if db_error:
            return db_error

        # Check Redis connection
        redis_error = self.check_redis(data, self.filter_worker_data)
        if redis_error:
            return redis_error

        # Check online workers
        if data.get("online_workers", 0) == 0:
            return self.create_workers_error_response(data, self.filter_worker_data)

        return Response(self.filter_worker_data(data), status=status.HTTP_200_OK)


# Keep the original PingView for backward compatibility
class PingView(BasePingView):
    """
    Original ping endpoint that checks all system components.

    Returns error status when:
    - Database isn't connected
    - Redis isn't connected
    - online_api_apps == 0
    - online_content_apps == 0
    - online_workers == 0
    """

    def get(self, request, *args, **kwargs):
        data, error_response = self.get_status_data(request, *args, **kwargs)

        if error_response:
            return error_response

        # Check database connection
        db_error = self.check_database(data)
        if db_error:
            return db_error

        # Check Redis connection
        redis_error = self.check_redis(data)
        if redis_error:
            return redis_error

        # Check online API apps
        if data.get("online_api_apps", 0) == 0:
            return self.create_api_apps_error_response(data)

        # Check online content apps
        if data.get("online_content_apps", 0) == 0:
            return self.create_content_apps_error_response(data)

        # Check online workers
        if data.get("online_workers", 0) == 0:
            return self.create_workers_error_response(data)

        data["versions"] = get_galaxy_ng_versions()

        return Response(data, status=status.HTTP_200_OK)
