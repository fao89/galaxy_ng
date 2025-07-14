
from unittest import mock
from unittest.mock import MagicMock

from django.test import override_settings

from galaxy_ng.app import pipelines


@override_settings(KEYCLOAK_ROLE_TOKEN_CLAIM='roles', KEYCLOAK_ADMIN_ROLE='admin')
def test_user_role_is_admin():
    user = MagicMock()
    response = {'roles': ['admin', 'user']}
    pipelines.user_role(response, {}, user=user)
    assert user.is_staff is True
    assert user.is_admin is True
    assert user.is_superuser is True
    user.save.assert_called_once()


@override_settings(KEYCLOAK_ROLE_TOKEN_CLAIM='roles', KEYCLOAK_ADMIN_ROLE='admin')
def test_user_role_not_admin():
    user = MagicMock()
    response = {'roles': ['user']}
    pipelines.user_role(response, {}, user=user)
    assert user.is_staff is False
    assert user.is_admin is False
    assert user.is_superuser is False
    user.save.assert_called_once()


@override_settings(KEYCLOAK_GROUP_TOKEN_CLAIM='groups')
@mock.patch('galaxy_ng.app.pipelines.Group')
def test_user_group(mock_group):
    user = MagicMock()
    group1 = MagicMock()
    group2 = MagicMock()
    mock_group.objects.get_or_create.side_effect = [(group1, True), (group2, False)]
    response = {'groups': ['/group1', '/group2']}

    pipelines.user_group(response, {}, user=user)

    user.groups.clear.assert_called_once()
    group1.user_set.add.assert_called_once_with(user)
    group2.user_set.add.assert_called_once_with(user)
