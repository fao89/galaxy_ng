
from unittest import mock

from django.core.exceptions import ObjectDoesNotExist

from galaxy_ng.app.tasks import index_registry


def test_parse_catalog_repositories():
    response_data = {
        'data': [{
            'repository': 'test_repo',
            'display_data': {
                'short_description': 'short desc',
                'long_description_markdown': 'long desc'
            }
        }]
    }
    containers = index_registry._parse_catalog_repositories(response_data)
    assert containers[0]['name'] == 'test_repo'
    assert containers[0]['description'] == 'short desc'
    assert containers[0]['readme'] == 'long desc'


@mock.patch('galaxy_ng.app.tasks.index_registry.models.ContainerDistroReadme')
def test_update_distro_readme_and_description(mock_readme):
    mock_distro = mock.Mock()
    mock_readme_obj = mock.Mock()
    mock_readme.objects.get_or_create.return_value = (mock_readme_obj, True)
    container_data = {'readme': 'new readme', 'description': 'new desc'}

    index_registry._update_distro_readme_and_description(mock_distro, container_data)

    assert mock_readme_obj.text == 'new readme'
    mock_readme_obj.save.assert_called_once()
    assert mock_distro.description == 'new desc'
    mock_distro.save.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerDistribution')
@mock.patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRepos')
@mock.patch('galaxy_ng.app.tasks.index_registry._update_distro_readme_and_description')
def test_create_or_update_remote_container_update(
    mock_update, mock_registry_repos, mock_distro
):
    mock_distro_obj = mock.Mock()
    mock_distro.objects.get.return_value = mock_distro_obj
    mock_repo = mock.Mock()
    mock_repo.pulp_type = 'container.containerrepository'
    mock_distro_obj.repository = mock_repo
    mock_registry_repo = mock.Mock()
    mock_registry_repo.registry.pk = 1
    mock_registry_repos.objects.get.return_value = mock_registry_repo

    container_data = {'name': 'test_container'}
    index_registry.create_or_update_remote_container(container_data, 1, {})
    mock_update.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.index_registry.container_models.ContainerDistribution')
@mock.patch('galaxy_ng.app.tasks.index_registry.serializers.ContainerRemoteSerializer')
@mock.patch('galaxy_ng.app.tasks.index_registry._update_distro_readme_and_description')
def test_create_or_update_remote_container_create(
    mock_update, mock_serializer, mock_distro
):
    mock_distro.objects.get.side_effect = ObjectDoesNotExist
    mock_serializer_instance = mock.Mock()
    mock_serializer.return_value = mock_serializer_instance

    container_data = {'name': 'test_container'}
    index_registry.create_or_update_remote_container(container_data, 1, {})
    mock_serializer_instance.is_valid.assert_called_once()
    mock_serializer_instance.create.assert_called_once()
    mock_update.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.index_registry.models.ContainerRegistryRemote')
@mock.patch('galaxy_ng.app.tasks.index_registry.dispatch')
def test_index_execution_environments_from_redhat_registry(
    mock_dispatch, mock_registry
):
    mock_registry_obj = mock.Mock()
    mock_registry.objects.get.return_value = mock_registry_obj
    mock_downloader = mock.Mock()
    path = "galaxy_ng/tests/unit/app/tasks/fixtures/catalog_response.json"
    mock_downloader.fetch.return_value.path = path
    mock_registry_obj.get_downloader.return_value = mock_downloader

    index_registry.index_execution_environments_from_redhat_registry(1, {})
    mock_dispatch.assert_called()
