
from unittest import mock

from django.test import override_settings
from rest_framework import exceptions

from galaxy_ng.app.auth import keycloak


@override_settings(
    SOCIAL_AUTH_KEYCLOAK_KEY='test_key',
    SOCIAL_AUTH_KEYCLOAK_SECRET='test_secret',
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL='http://test.com/token',
    GALAXY_VERIFY_KEYCLOAK_SSL_CERTS=False
)
@mock.patch('requests.post')
@mock.patch('galaxy_ng.app.auth.keycloak.load_strategy')
def test_authenticate_credentials_success(mock_load_strategy, mock_post):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'test_token'}
    mock_post.return_value = mock_response

    mock_strategy = mock.Mock()
    mock_load_strategy.return_value = mock_strategy
    mock_strategy.authenticate.return_value = mock.Mock()

    auth = keycloak.KeycloakBasicAuth()
    user, _ = auth.authenticate_credentials('test_user', 'test_pass')

    assert user is not None
    mock_post.assert_called_once()
    mock_strategy.authenticate.assert_called_once()


@override_settings(
    SOCIAL_AUTH_KEYCLOAK_KEY='test_key',
    SOCIAL_AUTH_KEYCLOAK_SECRET='test_secret',
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL='http://test.com/token',
    GALAXY_VERIFY_KEYCLOAK_SSL_CERTS=False
)
@mock.patch('requests.post')
@mock.patch('rest_framework.authentication.BasicAuthentication.authenticate_credentials')
def test_authenticate_credentials_failure(mock_basic_auth, mock_post):
    mock_response = mock.Mock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response

    auth = keycloak.KeycloakBasicAuth()
    auth.authenticate_credentials('test_user', 'test_pass')

    mock_basic_auth.assert_called_once()


@override_settings(
    SOCIAL_AUTH_KEYCLOAK_KEY='test_key',
    SOCIAL_AUTH_KEYCLOAK_SECRET='test_secret',
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL='http://test.com/token',
    GALAXY_VERIFY_KEYCLOAK_SSL_CERTS=False
)
@mock.patch('requests.post')
@mock.patch('galaxy_ng.app.auth.keycloak.load_strategy')
def test_authenticate_credentials_no_user(mock_load_strategy, mock_post):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'test_token'}
    mock_post.return_value = mock_response

    mock_strategy = mock.Mock()
    mock_load_strategy.return_value = mock_strategy
    mock_strategy.authenticate.return_value = None

    auth = keycloak.KeycloakBasicAuth()
    with exceptions.AuthenticationFailed as e:
        auth.authenticate_credentials('test_user', 'test_pass')
        assert 'Authentication failed' in str(e)


@override_settings(
    SOCIAL_AUTH_KEYCLOAK_KEY='test_key',
    SOCIAL_AUTH_KEYCLOAK_SECRET='test_secret',
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL='http://test.com/token',
    GALAXY_VERIFY_KEYCLOAK_SSL_CERTS=False
)
@mock.patch('requests.post')
@mock.patch('galaxy_ng.app.auth.keycloak.load_strategy', side_effect=AttributeError)
def test_authenticate_credentials_attribute_error(mock_load_strategy, mock_post):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'test_token'}
    mock_post.return_value = mock_response

    auth = keycloak.KeycloakBasicAuth()
    result = auth.authenticate_credentials('test_user', 'test_pass')
    assert result is None
