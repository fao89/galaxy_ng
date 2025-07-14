
from unittest import mock

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.api.ui.v1.views import signing


class TestCollectionSignView:

    @mock.patch('galaxy_ng.app.api.ui.v1.views.signing.call_sign_task')
    def test_post(self, mock_call_sign):
        view = signing.CollectionSignView()
        view._get_signing_service = mock.Mock()
        view.get_repository = mock.Mock()
        view._get_content_units_to_sign = mock.Mock()
        mock_call_sign.return_value = mock.Mock(pk=1)

        request = mock.Mock()
        response = view.post(request)

        assert response.status_code == 202
        assert response.data['task_id'] == 1

    def test_get_content_units_to_sign_from_list(self):
        view = signing.CollectionSignView()
        request = mock.Mock()
        request.data = {'content_units': ['1', '2', '3']}
        units = view._get_content_units_to_sign(request, None)
        assert units == ['1', '2', '3']

    @mock.patch('galaxy_ng.app.api.ui.v1.views.signing.AnsibleDistribution')
    def test_get_repository(self, mock_distro):
        view = signing.CollectionSignView()
        view.kwargs = {'path': 'test_distro'}
        request = mock.Mock()
        repo = view.get_repository(request)
        assert repo is not None

    def test_get_repository_no_distro(self):
        view = signing.CollectionSignView()
        view.kwargs = {}
        request = mock.Mock()
        request.data = {}
        with ValidationError as e:
            view.get_repository(request)
            assert 'distro_base_path' in str(e)

    @mock.patch('galaxy_ng.app.api.ui.v1.views.signing.SigningService')
    def test_get_signing_service(self, mock_signing_service):
        view = signing.CollectionSignView()
        request = mock.Mock()
        request.data = {'signing_service': 'test_service'}
        service = view._get_signing_service(request)
        assert service is not None

    def test_get_signing_service_no_service(self):
        view = signing.CollectionSignView()
        request = mock.Mock()
        request.data = {}
        with ValidationError as e:
            view._get_signing_service(request)
            assert 'signing_service' in str(e)

    @mock.patch('galaxy_ng.app.api.ui.v1.views.signing.SigningService')
    def test_get_signing_service_not_found(self, mock_signing_service):
        mock_signing_service.objects.get.side_effect = ObjectDoesNotExist
        view = signing.CollectionSignView()
        request = mock.Mock()
        request.data = {'signing_service': 'test_service'}
        with ValidationError as e:
            view._get_signing_service(request)
            assert 'does not exist' in str(e)
