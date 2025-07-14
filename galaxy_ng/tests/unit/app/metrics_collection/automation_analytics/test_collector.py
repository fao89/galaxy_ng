
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.metrics_collection.automation_analytics import collector


class TestCollector:

    @override_settings(GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED=True)
    @mock.patch('galaxy_ng.app.metrics_collection.collector.Collector.is_enabled')
    def test_is_enabled_true(self, mock_super_is_enabled):
        c = collector.Collector()
        assert c.is_enabled() is True

    @override_settings(GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED=False)
    def test_is_enabled_false(self):
        c = collector.Collector()
        assert c.is_enabled() is False

    @override_settings(
        GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL='http://test.com',
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE='userpass',
        GALAXY_METRICS_COLLECTION_REDHAT_USERNAME='user',
        GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD='password'
    )
    def test_is_shipping_configured_userpass(self):
        c = collector.Collector()
        assert c._is_shipping_configured() is True

    @override_settings(
        GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL='http://test.com',
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE='identity',
        GALAXY_METRICS_COLLECTION_ORG_ID='12345'
    )
    def test_is_shipping_configured_identity(self):
        c = collector.Collector()
        assert c._is_shipping_configured() is True

    @override_settings(GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL=None)
    def test_is_shipping_configured_false(self):
        c = collector.Collector()
        assert c._is_shipping_configured() is False
