from unittest import mock

from django.test import override_settings
from django.urls import reverse

from rest_framework import status as http_status
from rest_framework.response import Response

from galaxy_ng.app.api.ping import PingView, PingApiView, PingContentView, PingWorkerView
from galaxy_ng.tests.unit.api.base import BaseTestCase


class TestPingView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.ping_url = reverse("galaxy:api:ping")

    @mock.patch.object(PingView, 'get')
    def test_ping_success_all_systems_healthy(self, mock_super_get):
        """Test ping endpoint returns 200 when all systems are healthy"""
        # Mock the parent StatusView response with healthy status
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 3,
            "versions": {"pulpcore": "3.25.0"}
        }, status=http_status.HTTP_200_OK)

        # Create a real PingView instance and call the actual get method
        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertIn("database_connection", response.data)

    @mock.patch.object(PingView, 'get')
    def test_ping_database_disconnected(self, mock_super_get):
        """Test ping endpoint returns 503 when database is disconnected"""
        mock_response = Response({
            "database_connection": {"connected": False},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "Database is not connected")

    @mock.patch.object(PingView, 'get')
    @override_settings(CACHE_ENABLED=True)
    def test_ping_redis_disconnected_cache_enabled(self, mock_super_get):
        """Test ping endpoint returns 503 when Redis is disconnected and cache is enabled"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": False},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "Redis is not connected")

    @mock.patch.object(PingView, 'get')
    @override_settings(CACHE_ENABLED=False)
    def test_ping_redis_disconnected_cache_disabled(self, mock_super_get):
        """Test ping endpoint ignores Redis when cache is disabled"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": False},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

    @mock.patch.object(PingView, 'get')
    def test_ping_no_api_apps(self, mock_super_get):
        """Test ping endpoint returns 503 when no API apps are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 0,
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online API apps available")

    @mock.patch.object(PingView, 'get')
    def test_ping_no_content_apps(self, mock_super_get):
        """Test ping endpoint returns 503 when no content apps are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 0,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online content apps available")

    @mock.patch.object(PingView, 'get')
    def test_ping_no_workers(self, mock_super_get):
        """Test ping endpoint returns 503 when no workers are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 0
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online workers available")

    @mock.patch.object(PingView, 'get')
    def test_ping_parent_status_view_error(self, mock_super_get):
        """Test ping endpoint returns parent StatusView error when it fails"""
        mock_response = Response({
            "error": "Internal server error"
        }, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_500_INTERNAL_SERVER_ERROR)

    @mock.patch.object(PingView, 'get')
    def test_ping_missing_data_fields(self, mock_super_get):
        """Test ping endpoint handles missing data fields gracefully"""
        # StatusView response with missing some fields
        mock_response = Response({
            "database_connection": {"connected": True},
            # redis_connection missing
            # online_api_apps missing
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        # Should fail on missing online_api_apps (defaults to 0)
        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online API apps available")

    @mock.patch.object(PingView, 'get')
    def test_ping_database_connection_missing_connected_field(self, mock_super_get):
        """Test ping endpoint handles missing connected field in database_connection"""
        mock_response = Response({
            "database_connection": {},  # missing 'connected' field
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)

        view = PingView()
        view.request = self.client.get(self.ping_url).wsgi_request

        with mock.patch('galaxy_ng.app.api.ping.StatusView.get', return_value=mock_response):
            response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "Database is not connected")

    def test_ping_view_inherits_from_status_view(self):
        """Test that PingView properly inherits from StatusView"""
        from pulpcore.app.views import StatusView
        self.assertTrue(issubclass(PingView, StatusView))

    def test_ping_url_mapping(self):
        """Test that ping URL is properly mapped"""
        url = reverse("galaxy:api:ping")
        self.assertEqual(url, "/api/automation-hub/ping/")


class TestPingApiView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.ping_url = reverse("galaxy:api:ping-api")

    @mock.patch('galaxy_ng.app.api.ping.get_galaxy_ng_versions')
    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_api_success(self, mock_super_get, mock_get_versions):
        """Test ping/api/ endpoint returns 200 when API apps are healthy"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 5,  # Should not appear in response
            "online_workers": 3,       # Should not appear in response
            "storage": {"total": 1000, "used": 500},
            "versions": {"pulpcore": "3.25.0"}
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        mock_get_versions.return_value = {
            "galaxy_ng_version": "4.12.0",
            "pulpcore_version": "3.49.0",
            "pulp_ansible_version": "0.25.1",
            "django_version": "4.2.25"
        }

        view = PingApiView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        # Verify only API-related data is returned
        expected_keys = {
            "database_connection", "redis_connection", "online_api_apps", "storage", "versions"
        }
        self.assertEqual(set(response.data.keys()), expected_keys)
        self.assertEqual(response.data["online_api_apps"], 2)
        self.assertNotIn("online_content_apps", response.data)
        self.assertNotIn("online_workers", response.data)

        # Verify enhanced versions are included
        self.assertIn("versions", response.data)
        versions = response.data["versions"]
        self.assertIn("galaxy_ng_version", versions)
        self.assertIn("pulpcore_version", versions)

    @mock.patch('galaxy_ng.app.api.ping.get_galaxy_ng_versions')
    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_api_no_api_apps(self, mock_super_get, mock_get_versions):
        """Test ping/api/ endpoint returns 503 when no API apps are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 0,
            "online_content_apps": 1,
            "online_workers": 3,
            "storage": {"total": 1000, "used": 500},
            "versions": {"pulpcore": "3.25.0"}
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        mock_get_versions.return_value = {
            "galaxy_ng_version": "4.12.0",
            "pulpcore_version": "3.49.0",
            "pulp_ansible_version": "0.25.1",
            "django_version": "4.2.25"
        }

        view = PingApiView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online API apps available")
        # Verify only API-related data is returned in error response
        expected_keys = {
            "database_connection", "redis_connection", "online_api_apps", "storage", "versions"
        }
        self.assertEqual(set(response.data["data"].keys()), expected_keys)
        self.assertNotIn("online_content_apps", response.data["data"])
        self.assertNotIn("online_workers", response.data["data"])

    def test_ping_api_url_mapping(self):
        """Test that ping/api/ URL is properly mapped"""
        url = reverse("galaxy:api:ping-api")
        self.assertEqual(url, "/api/automation-hub/ping/api/")


class TestPingContentView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.ping_url = reverse("galaxy:api:ping-content")

    @mock.patch('galaxy_ng.app.api.ping.get_galaxy_ng_versions')
    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_content_success(self, mock_super_get, mock_get_versions):
        """Test ping/content/ endpoint returns 200 when content apps are healthy"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,      # Should not appear in response
            "online_content_apps": 1,
            "online_workers": 3,       # Should not appear in response
            "storage": {"total": 1000, "used": 500},
            "content_settings": {"workers": 3},
            "versions": {"pulpcore": "3.25.0"}
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        mock_get_versions.return_value = {
            "galaxy_ng_version": "4.12.0",
            "pulpcore_version": "3.49.0",
            "pulp_ansible_version": "0.25.1",
            "django_version": "4.2.25"
        }

        view = PingContentView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        # Verify only content-related data is returned
        expected_keys = {
            "database_connection", "redis_connection", "online_content_apps",
            "storage", "content_settings", "versions"
        }
        self.assertEqual(set(response.data.keys()), expected_keys)
        self.assertEqual(response.data["online_content_apps"], 1)
        self.assertNotIn("online_api_apps", response.data)
        self.assertNotIn("online_workers", response.data)

        # Verify enhanced versions are included
        self.assertIn("versions", response.data)
        versions = response.data["versions"]
        self.assertIn("galaxy_ng_version", versions)
        self.assertIn("pulpcore_version", versions)

    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_content_no_content_apps(self, mock_super_get):
        """Test ping/content/ endpoint returns 503 when no content apps are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 0,
            "online_workers": 3
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        view = PingContentView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online content apps available")

    def test_ping_content_url_mapping(self):
        """Test that ping/content/ URL is properly mapped"""
        url = reverse("galaxy:api:ping-content")
        self.assertEqual(url, "/api/automation-hub/ping/content/")


class TestPingWorkerView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.ping_url = reverse("galaxy:api:ping-worker")

    @mock.patch('galaxy_ng.app.api.ping.get_galaxy_ng_versions')
    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_worker_success(self, mock_super_get, mock_get_versions):
        """Test ping/worker/ endpoint returns 200 when workers are healthy"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,      # Should not appear in response
            "online_content_apps": 1,  # Should not appear in response
            "online_workers": 3,
            "storage": {"total": 1000, "used": 500},
            "versions": {"pulpcore": "3.25.0"}
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        mock_get_versions.return_value = {
            "galaxy_ng_version": "4.12.0",
            "pulpcore_version": "3.49.0",
            "pulp_ansible_version": "0.25.1",
            "django_version": "4.2.25"
        }

        view = PingWorkerView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        # Verify only worker-related data is returned
        expected_keys = {
            "database_connection", "redis_connection", "online_workers", "storage", "versions"
        }
        self.assertEqual(set(response.data.keys()), expected_keys)
        self.assertEqual(response.data["online_workers"], 3)
        self.assertNotIn("online_api_apps", response.data)
        self.assertNotIn("online_content_apps", response.data)

        # Verify enhanced versions are included
        self.assertIn("versions", response.data)
        versions = response.data["versions"]
        self.assertIn("galaxy_ng_version", versions)
        self.assertIn("pulpcore_version", versions)

    @mock.patch('galaxy_ng.app.api.ping.StatusView.get')
    def test_ping_worker_no_workers(self, mock_super_get):
        """Test ping/worker/ endpoint returns 503 when no workers are online"""
        mock_response = Response({
            "database_connection": {"connected": True},
            "redis_connection": {"connected": True},
            "online_api_apps": 2,
            "online_content_apps": 1,
            "online_workers": 0
        }, status=http_status.HTTP_200_OK)
        mock_super_get.return_value = mock_response

        view = PingWorkerView()
        view.request = self.client.get(self.ping_url).wsgi_request
        response = view.get(view.request)

        self.assertEqual(response.status_code, http_status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["error"], "No online workers available")

    def test_ping_worker_url_mapping(self):
        """Test that ping/worker/ URL is properly mapped"""
        url = reverse("galaxy:api:ping-worker")
        self.assertEqual(url, "/api/automation-hub/ping/worker/")
