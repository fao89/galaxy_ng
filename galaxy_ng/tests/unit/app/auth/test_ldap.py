
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.auth import ldap


class TestGalaxyLDAPSettings:

    @override_settings(GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS=True)
    @mock.patch('galaxy_ng.app.auth.ldap.Group')
    def test_mirror_groups_enabled(self, mock_group):
        mock_group.objects.all.return_value.values_list.return_value = {'group1', 'group2'}
        settings = ldap.GalaxyLDAPSettings()
        settings.MIRROR_GROUPS = {'group3'}

        assert settings.MIRROR_GROUPS == {'group1', 'group2', 'group3'}

    @override_settings(GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS=False)
    def test_mirror_groups_disabled(self):
        settings = ldap.GalaxyLDAPSettings()
        settings.MIRROR_GROUPS = {'group3'}

        assert settings.MIRROR_GROUPS == {'group3'}


class TestPrefixedLDAPBackend:

    @override_settings(RENAMED_USERNAME_PREFIX='ldap-')
    @mock.patch('galaxy_ng.app.auth.ldap.GalaxyLDAPBackend.authenticate')
    def test_authenticate_prefixed(self, mock_super_auth):
        backend = ldap.PrefixedLDAPBackend()
        backend.authenticate(username='ldap-test_user')
        mock_super_auth.assert_called_once_with(username='test_user')

    @override_settings(RENAMED_USERNAME_PREFIX='ldap-')
    @mock.patch('galaxy_ng.app.auth.ldap.GalaxyLDAPBackend.authenticate')
    def test_authenticate_not_prefixed(self, mock_super_auth):
        backend = ldap.PrefixedLDAPBackend()
        backend.authenticate(username='test_user')
        mock_super_auth.assert_called_once_with(username='test_user')

    @override_settings(RENAMED_USERNAME_PREFIX='ldap-')
    @mock.patch('galaxy_ng.app.auth.ldap.User')
    @mock.patch('galaxy_ng.app.auth.ldap.GalaxyLDAPBackend.get_or_build_user')
    def test_get_or_build_user_prefixed_exists(self, mock_super_get, mock_user):
        mock_user.objects.filter.return_value = True
        backend = ldap.PrefixedLDAPBackend()
        backend.get_or_build_user('test_user', None)
        mock_super_get.assert_called_once_with('ldap-test_user', None)

    @override_settings(RENAMED_USERNAME_PREFIX='ldap-')
    @mock.patch('galaxy_ng.app.auth.ldap.User')
    @mock.patch('galaxy_ng.app.auth.ldap.GalaxyLDAPBackend.get_or_build_user')
    def test_get_or_build_user_prefixed_does_not_exist(self, mock_super_get, mock_user):
        mock_user.objects.filter.return_value = False
        backend = ldap.PrefixedLDAPBackend()
        backend.get_or_build_user('test_user', None)
        mock_super_get.assert_called_once_with('test_user', None)
