
from unittest import mock

from galaxy_ng.app.utils import rbac


@mock.patch('galaxy_ng.app.utils.rbac.User')
@mock.patch('galaxy_ng.app.utils.rbac.Group')
@mock.patch('galaxy_ng.app.utils.rbac.add_user_to_group')
def test_add_username_to_groupname(mock_add_user, mock_group, mock_user):
    mock_user_obj = mock.Mock()
    mock_user.objects.filter.return_value.first.return_value = mock_user_obj
    mock_group_obj = mock.Mock()
    mock_group.objects.filter.return_value.first.return_value = mock_group_obj

    rbac.add_username_to_groupname('test_user', 'test_group')
    mock_add_user.assert_called_once_with(mock_user_obj, mock_group_obj)


@mock.patch('galaxy_ng.app.utils.rbac.User')
@mock.patch('galaxy_ng.app.utils.rbac.Group')
@mock.patch('galaxy_ng.app.utils.rbac.remove_user_from_group')
def test_remove_username_from_groupname(mock_remove_user, mock_group, mock_user):
    mock_user_obj = mock.Mock()
    mock_user.objects.filter.return_value.first.return_value = mock_user_obj
    mock_group_obj = mock.Mock()
    mock_group.objects.filter.return_value.first.return_value = mock_group_obj

    rbac.remove_username_from_groupname('test_user', 'test_group')
    mock_remove_user.assert_called_once_with(mock_user_obj, mock_group_obj)


@mock.patch('galaxy_ng.app.utils.rbac.Group')
@mock.patch('galaxy_ng.app.utils.rbac.Namespace')
@mock.patch('galaxy_ng.app.utils.rbac.add_group_to_v3_namespace')
def test_add_groupname_to_v3_namespace_name(
    mock_add_group, mock_namespace, mock_group
):
    mock_group_obj = mock.Mock()
    mock_group.objects.filter.return_value.first.return_value = mock_group_obj
    mock_ns_obj = mock.Mock()
    mock_namespace.objects.filter.return_value.first.return_value = mock_ns_obj

    rbac.add_groupname_to_v3_namespace_name('test_group', 'test_ns')
    mock_add_group.assert_called_once_with(mock_group_obj, mock_ns_obj)


@mock.patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
@mock.patch('galaxy_ng.app.utils.rbac.assign_role')
def test_add_group_to_v3_namespace(mock_assign_role, mock_get_groups):
    mock_group = mock.Mock()
    mock_ns = mock.Mock()
    mock_get_groups.return_value = []

    rbac.add_group_to_v3_namespace(mock_group, mock_ns)
    mock_assign_role.assert_called_once_with(
        'galaxy.collection_namespace_owner', mock_group, mock_ns
    )


@mock.patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
@mock.patch('galaxy_ng.app.utils.rbac.remove_role')
def test_remove_group_from_v3_namespace(mock_remove_role, mock_get_groups):
    mock_group = mock.Mock()
    mock_ns = mock.Mock()
    mock_get_groups.return_value = [mock_group]

    rbac.remove_group_from_v3_namespace(mock_group, mock_ns)
    mock_remove_role.assert_called_once_with(
        'galaxy.collection_namespace_owner', mock_group, mock_ns
    )


@mock.patch('galaxy_ng.app.utils.rbac.assign_role')
def test_add_user_to_v3_namespace(mock_assign_role):
    mock_user = mock.Mock()
    mock_ns = mock.Mock()
    rbac.add_user_to_v3_namespace(mock_user, mock_ns)
    mock_assign_role.assert_called_once_with(
        'galaxy.collection_namespace_owner', mock_user, mock_ns
    )


@mock.patch('galaxy_ng.app.utils.rbac.remove_role')
def test_remove_user_from_v3_namespace(mock_remove_role):
    mock_user = mock.Mock()
    mock_ns = mock.Mock()
    rbac.remove_user_from_v3_namespace(mock_user, mock_ns)
    mock_remove_role.assert_called_once_with(
        'galaxy.collection_namespace_owner', mock_user, mock_ns
    )


@mock.patch('galaxy_ng.app.utils.rbac.get_groups_with_perms_attached_roles')
@mock.patch('galaxy_ng.app.utils.rbac.get_users_with_perms_attached_roles')
def test_get_v3_namespace_owners(mock_get_users, mock_get_groups):
    mock_user1 = mock.Mock()
    mock_user2 = mock.Mock()
    mock_group = mock.Mock()
    mock_group.user_set.all.return_value = [mock_user1]
    mock_get_groups.return_value = [mock_group]
    mock_get_users.return_value = [mock_user2]

    owners = rbac.get_v3_namespace_owners(mock.Mock())
    assert owners == [mock_user1, mock_user2]


@mock.patch('galaxy_ng.app.utils.rbac.Role')
@mock.patch('galaxy_ng.app.utils.rbac.get_objects_for_user')
def test_get_owned_v3_namespaces(mock_get_objects, mock_role):
    mock_user = mock.Mock()
    mock_role_obj = mock.Mock()
    mock_role.objects.filter.return_value.first.return_value = mock_role_obj
    mock_get_objects.return_value = ['ns1', 'ns2']

    namespaces = rbac.get_owned_v3_namespaces(mock_user)
    assert namespaces == ['ns1', 'ns2']
