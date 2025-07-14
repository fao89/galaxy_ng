
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.tasks import publishing


@mock.patch('galaxy_ng.app.tasks.publishing.Task')
@mock.patch('galaxy_ng.app.tasks.publishing.ContentType')
def test_get_created_collection_versions(mock_content_type, mock_task):
    mock_task_instance = mock.Mock()
    mock_task.current.return_value = mock_task_instance
    mock_created_resource = mock.Mock()
    mock_task_instance.created_resources.filter.return_value = [mock_created_resource]

    versions = publishing.get_created_collection_versions()
    assert len(versions) == 1


@mock.patch('galaxy_ng.app.tasks.publishing.general_create')
@mock.patch('galaxy_ng.app.tasks.publishing.AnsibleRepository')
def test_upload_collection(mock_repo, mock_general_create):
    mock_repo_obj = mock.Mock()
    mock_repo.objects.get.return_value = mock_repo_obj
    kwargs = {
        'repository_pk': 1,
        'general_args': [],
        'data': {'repository': 'test_repo'}
    }
    repo = publishing._upload_collection(**kwargs)
    assert repo == mock_repo_obj
    mock_general_create.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.publishing._upload_collection')
@mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
@mock.patch('galaxy_ng.app.tasks.publishing.dispatch')
@mock.patch('galaxy_ng.app.tasks.publishing.Namespace')
@override_settings(GALAXY_ENABLE_API_ACCESS_LOG=True)
def test_import_to_staging(mock_namespace, mock_dispatch, mock_get_versions, mock_upload):
    mock_cv = mock.Mock()
    mock_get_versions.return_value = [mock_cv]
    publishing.import_to_staging('test_user')
    mock_dispatch.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.publishing._upload_collection')
@mock.patch('galaxy_ng.app.tasks.publishing.get_created_collection_versions')
@mock.patch('galaxy_ng.app.tasks.publishing.call_auto_approve_task')
@mock.patch('galaxy_ng.app.tasks.publishing.Namespace')
@override_settings(GALAXY_ENABLE_API_ACCESS_LOG=True)
def test_import_and_auto_approve(
    mock_namespace, mock_call_auto_approve, mock_get_versions, mock_upload
):
    mock_cv = mock.Mock()
    mock_get_versions.return_value = [mock_cv]
    publishing.import_and_auto_approve('test_user')
    mock_call_auto_approve.assert_called_once()


@mock.patch('logging.getLogger')
def test_log_collection_upload(mock_get_logger):
    mock_logger = mock.Mock()
    mock_get_logger.return_value = mock_logger
    publishing._log_collection_upload('test_user', 'test_ns', 'test_name', '1.0.0')
    mock_logger.info.assert_called_once()
