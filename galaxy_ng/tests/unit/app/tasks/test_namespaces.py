
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import override_settings
from pulpcore.plugin.models import Artifact

from galaxy_ng.app.tasks import namespaces


@override_settings(MAX_AVATAR_SIZE=100)
@mock.patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
@mock.patch('galaxy_ng.app.tasks.namespaces.ImageField')
@mock.patch('galaxy_ng.app.tasks.namespaces.PulpTemporaryUploadedFile')
@mock.patch.object(Artifact, 'init_and_validate')
def test_download_avatar_success(
    mock_init_and_validate,
    mock_pulp_tmp_file,
    mock_image_field,
    mock_downloader
):
    mock_downloader_instance = mock.Mock()
    mock_downloader_instance.fetch.return_value.artifact_attributes = {'size': 50}
    mock_downloader.return_value = mock_downloader_instance

    namespaces._download_avatar('http://test.com/avatar.png', 'test_ns')

    mock_init_and_validate.assert_called_once()


@override_settings(MAX_AVATAR_SIZE=100)
@mock.patch('galaxy_ng.app.tasks.namespaces.HttpDownloader')
def test_download_avatar_too_large(mock_downloader):
    mock_downloader_instance = mock.Mock()
    mock_downloader_instance.fetch.return_value.artifact_attributes = {'size': 150}
    mock_downloader.return_value = mock_downloader_instance

    with ValidationError as e:
        namespaces._download_avatar('http://test.com/avatar.png', 'test_ns')
        assert 'larger than' in str(e)


@mock.patch('galaxy_ng.app.tasks.namespaces.add_and_remove')
def test_add_namespace_metadata_to_repos(mock_add_and_remove):
    namespaces._add_namespace_metadata_to_repos(1, [2, 3])
    assert mock_add_and_remove.call_count == 2
