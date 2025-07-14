
from unittest.mock import MagicMock

from django.test import override_settings

from galaxy_ng.app.common import openapi


def test_preprocess_exclude_endpoints():
    endpoints = [
        ('/pulp/api/v3/status/', '', 'GET', ''),
        ('/pulp/api/v3/collections/', '', 'GET', ''),
        ('/api/v3/collections/', '', 'GET', ''),
        ('/api/_ui/collections/', '', 'GET', ''),
    ]

    filtered_endpoints = openapi.preprocess_exclude_endpoints(endpoints)

    assert len(filtered_endpoints) == 2
    assert filtered_endpoints[0][0] == '/pulp/api/v3/status/'
    assert filtered_endpoints[1][0] == '/api/v3/collections/'


@override_settings(
    GALAXY_CORS_ALLOWED_ORIGINS='http://localhost:8002',
    GALAXY_CORS_ALLOWED_HEADERS='Content-Type,Authorization'
)
def test_allow_cors_middleware():
    get_response = MagicMock()
    middleware = openapi.AllowCorsMiddleware(get_response)
    request = MagicMock()
    middleware(request)

    get_response.assert_called_once_with(request)
    response = get_response.return_value
    assert response['Access-Control-Allow-Origin'] == 'http://localhost:8002'
    assert response['Access-Control-Allow-Headers'] == 'Content-Type,Authorization'
