
from unittest import mock

from galaxy_ng.app.utils import legacy


def test_sanitize_avatar_url():
    url = 'https://example.com/avatar.png'
    sanitized = legacy.sanitize_avatar_url(f'"{url}"')
    assert sanitized == url

    url = 'http://example.com/avatar.png'
    sanitized = legacy.sanitize_avatar_url(f'"{url}"')
    assert sanitized == url

    sanitized = legacy.sanitize_avatar_url('not_a_url')
    assert sanitized is None


@mock.patch('galaxy_ng.app.utils.legacy.get_v3_namespace_owners')
@mock.patch('galaxy_ng.app.utils.legacy.add_user_to_v3_namespace')
@mock.patch('galaxy_ng.app.utils.legacy.generate_v3_namespace_from_attributes')
@mock.patch('galaxy_ng.app.utils.legacy.User')
@mock.patch('galaxy_ng.app.utils.legacy.Namespace')
@mock.patch('galaxy_ng.app.utils.legacy.LegacyNamespace')
def test_process_namespace(
    mock_legacy_namespace,
    mock_namespace,
    mock_user,
    mock_gen_v3,
    mock_add_user,
    mock_get_owners,
):
    mock_legacy_ns_obj = mock.Mock()
    mock_legacy_namespace.objects.get_or_create.return_value = (mock_legacy_ns_obj, True)
    mock_ns_obj = mock.Mock()
    mock_namespace.objects.get_or_create.return_value = (mock_ns_obj, True)
    mock_user_obj = mock.Mock()
    mock_user.objects.filter.return_value.first.return_value = mock_user_obj
    mock_gen_v3.return_value = 'test_v3_namespace'
    mock_get_owners.return_value = []

    namespace_info = {
        'id': 1,
        'summary_fields': {
            'owners': [{'username': 'test_user', 'github_id': '123'}]
        },
        'avatar_url': 'https://example.com/avatar.png',
        'company': 'Test Company',
        'email': 'test@example.com',
        'description': 'Test Description',
    }

    legacy.process_namespace('test_namespace', namespace_info)

    mock_legacy_namespace.objects.get_or_create.assert_called_once_with(name='test_namespace')
    mock_namespace.objects.get_or_create.assert_called_once_with(name='test_v3_namespace')
    mock_add_user.assert_called_once_with(mock_user_obj, mock_ns_obj)
    mock_ns_obj.save.assert_called()
