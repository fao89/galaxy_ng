
from unittest import mock

from galaxy_ng.app.tasks import registry_sync


@mock.patch('galaxy_ng.app.tasks.registry_sync.dispatch')
def test_launch_container_remote_sync(mock_dispatch):
    mock_remote = mock.Mock()
    mock_registry = mock.Mock()
    mock_registry.get_connection_fields.return_value = {'url': 'http://test.com'}
    mock_repo = mock.Mock()

    registry_sync.launch_container_remote_sync(mock_remote, mock_registry, mock_repo)

    assert mock_remote.url == 'http://test.com'
    mock_remote.save.assert_called_once()
    mock_dispatch.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.registry_sync.models.ContainerRegistryRemote')
@mock.patch('galaxy_ng.app.tasks.registry_sync.models.ContainerRegistryRepos')
@mock.patch('galaxy_ng.app.tasks.registry_sync.launch_container_remote_sync')
def test_sync_all_repos_in_registry(
    mock_launch_sync, mock_registry_repos, mock_registry
):
    mock_registry_obj = mock.Mock()
    mock_registry.objects.get.return_value = mock_registry_obj
    mock_remote_rel = mock.Mock()
    mock_registry_repos.objects.filter.return_value.all.return_value = [mock_remote_rel]
    mock_repo = mock.Mock()
    mock_remote_rel.repository_remote.repository_set.all.return_value = [mock_repo]

    registry_sync.sync_all_repos_in_registry(1)

    mock_launch_sync.assert_called_once_with(
        mock_remote_rel.repository_remote, mock_registry_obj, mock_repo
    )
