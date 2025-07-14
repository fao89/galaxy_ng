
import datetime
from unittest import mock

from django.utils import timezone
from django.test import override_settings
from rest_framework import exceptions
from rest_framework.authtoken.models import Token

from galaxy_ng.app.auth import token


@mock.patch.object(Token.objects, 'get')
def test_authenticate_credentials_valid(mock_get):
    mock_token = mock.Mock()
    mock_token.user.is_active = True
    mock_token.created = timezone.now()
    mock_get.return_value = mock_token

    auth = token.ExpiringTokenAuthentication()
    user, t = auth.authenticate_credentials('test_token')

    assert user == mock_token.user
    assert t == mock_token


@override_settings(GALAXY_TOKEN_EXPIRATION=60)
@mock.patch.object(Token.objects, 'get')
def test_authenticate_credentials_expired(mock_get):
    mock_token = mock.Mock()
    mock_token.user.is_active = True
    mock_token.created = timezone.now() - datetime.timedelta(minutes=61)
    mock_get.return_value = mock_token

    auth = token.ExpiringTokenAuthentication()
    with exceptions.AuthenticationFailed as e:
        auth.authenticate_credentials('test_token')
        assert 'Token has expired' in str(e)


@mock.patch.object(Token.objects, 'get')
def test_authenticate_credentials_no_social_auth(mock_get):
    mock_token = mock.Mock()
    mock_token.user.is_active = True
    mock_token.created = timezone.now() - datetime.timedelta(days=1)
    del mock_token.user.social_auth
    mock_get.return_value = mock_token

    auth = token.ExpiringTokenAuthentication()
    user, t = auth.authenticate_credentials('test_token')

    assert user == mock_token.user
    assert t == mock_token


@mock.patch.object(Token.objects, 'get', side_effect=Token.DoesNotExist)
def test_authenticate_credentials_invalid_token(mock_get):
    auth = token.ExpiringTokenAuthentication()
    with exceptions.AuthenticationFailed as e:
        auth.authenticate_credentials('test_token')
        assert 'Invalid token' in str(e)


@mock.patch.object(Token.objects, 'get')
def test_authenticate_credentials_inactive_user(mock_get):
    mock_token = mock.Mock()
    mock_token.user.is_active = False
    mock_get.return_value = mock_token

    auth = token.ExpiringTokenAuthentication()
    with exceptions.AuthenticationFailed as e:
        auth.authenticate_credentials('test_token')
        assert 'User inactive or deleted' in str(e)
