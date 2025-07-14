
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.tasks import promotion


@override_settings(
    GALAXY_AUTO_SIGN_COLLECTIONS=True, GALAXY_COLLECTION_SIGNING_SERVICE='test_service'
)
@mock.patch('galaxy_ng.app.tasks.promotion.AnsibleRepository')
@mock.patch('galaxy_ng.app.tasks.promotion.SigningService')
@mock.patch('galaxy_ng.app.tasks.promotion.add_and_remove')
@mock.patch('galaxy_ng.app.tasks.promotion.sign')
@mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
def test_auto_approve(
    mock_dispatch,
    mock_sign,
    mock_add_and_remove,
    mock_signing_service,
    mock_repo
):
    mock_repo_obj = mock.Mock()
    mock_repo_obj.pk = 1
    mock_repo.objects.get.return_value = mock_repo_obj
    mock_repo.objects.filter.return_value.values_list.return_value = [1]
    mock_signing_service_obj = mock.Mock()
    mock_signing_service.objects.get.return_value = mock_signing_service_obj

    promotion.auto_approve(1, 2, 3)

    mock_add_and_remove.assert_called_once_with(
        1, add_content_units=[2, 3], remove_content_units=[]
    )
    mock_sign.assert_called_once()
    mock_dispatch.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.promotion.TaskGroup')
@mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
def test_call_auto_approve_task(mock_dispatch, mock_task_group):
    mock_cv = mock.Mock()
    mock_repo = mock.Mock()
    mock_task_group_instance = mock.Mock()
    mock_task_group.current.return_value = mock_task_group_instance

    promotion.call_auto_approve_task(mock_cv, mock_repo, 1)

    mock_dispatch.assert_called_once()
    mock_task_group_instance.finish.assert_called_once()


@mock.patch('galaxy_ng.app.tasks.promotion.dispatch')
def test_call_move_content_task(mock_dispatch):
    mock_cv = mock.Mock()
    mock_src_repo = mock.Mock()
    mock_dest_repo = mock.Mock()

    promotion.call_move_content_task(mock_cv, mock_src_repo, mock_dest_repo)
    mock_dispatch.assert_called_once()
