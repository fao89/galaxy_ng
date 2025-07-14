
import base64
import json
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.metrics_collection.automation_analytics import package


class TestPackage:

    def test_tarname_base(self):
        mock_collector = mock.Mock()
        mock_collector.gather_until.strftime.return_value = '2022-01-01-0000'
        p = package.Package(mock_collector)
        assert p._tarname_base() == 'galaxy-hub-analytics-2022-01-01-0000'

    @override_settings(GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL='http://test.com')
    def test_get_ingress_url(self):
        p = package.Package(None)
        assert p.get_ingress_url() == 'http://test.com'

    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_USERNAME='user')
    def test_get_rh_user(self):
        p = package.Package(None)
        assert p._get_rh_user() == 'user'

    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD='password')
    def test_get_rh_password(self):
        p = package.Package(None)
        assert p._get_rh_password() == 'password'

    @override_settings(GALAXY_METRICS_COLLECTION_ORG_ID='12345')
    def test_get_x_rh_identity(self):
        p = package.Package(None)
        identity = p._get_x_rh_identity()
        decoded = json.loads(base64.b64decode(identity))
        assert decoded['identity']['account_number'] == '0012345'

    def test_hub_version(self):
        mock_collector = mock.Mock()
        mock_collector.collections.get.return_value.data = '{"hub_version": "1.2.3"}'
        p = package.Package(mock_collector)
        assert p.hub_version() == '1.2.3'

    def test_get_http_request_headers(self):
        mock_collector = mock.Mock()
        mock_collector.collections.get.return_value.data = '{"hub_version": "1.2.3"}'
        p = package.Package(mock_collector)
        headers = p._get_http_request_headers()
        assert headers['User-Agent'].startswith('GalaxyNG')

    @override_settings(GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE='userpass')
    def test_shipping_auth_mode(self):
        p = package.Package(None)
        assert p.shipping_auth_mode() == 'userpass'
