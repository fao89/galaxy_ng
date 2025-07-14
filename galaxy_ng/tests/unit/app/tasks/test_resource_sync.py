
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.tasks import resource_sync


@override_settings(RESOURCE_SERVER='http://test.com')
@mock.patch('galaxy_ng.app.tasks.resource_sync.SyncExecutor')
def test_run(mock_sync_executor):
    mock_executor_instance = mock.Mock()
    mock_sync_executor.return_value = mock_executor_instance
    mock_executor_instance.results = {'updated': ['resource1']}

    resource_sync.run()

    mock_sync_executor.assert_called_once_with(retries=3)
    mock_executor_instance.run.assert_called_once()


@override_settings(RESOURCE_SERVER=None)
@mock.patch('galaxy_ng.app.tasks.resource_sync.SyncExecutor')
def test_run_no_server(mock_sync_executor):
    resource_sync.run()
    mock_sync_executor.assert_not_called()
