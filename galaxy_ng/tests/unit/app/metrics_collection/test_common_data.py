
from unittest import mock

from django.test import override_settings

from galaxy_ng.app.metrics_collection import common_data


@mock.patch('requests.request')
def test_api_status_success(mock_request):
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'versions': []}
    mock_request.return_value = mock_response

    status = common_data.api_status()
    assert status == {'versions': []}


@mock.patch('requests.request')
def test_api_status_failure(mock_request):
    mock_response = mock.Mock()
    mock_response.status_code = 500
    mock_request.return_value = mock_response

    status = common_data.api_status()
    assert status == {}


@mock.patch('galaxy_ng.app.metrics_collection.common_data.api_status')
def test_hub_version(mock_api_status):
    mock_api_status.return_value = {
        'versions': [{'component': 'galaxy', 'version': '1.2.3'}]
    }
    version = common_data.hub_version()
    assert version == '1.2.3'


@override_settings(
    AUTHENTICATION_BACKENDS=['backend1'],
    GALAXY_DEPLOYMENT_MODE='standalone',
    ANSIBLE_API_HOSTNAME='http://test.com'
)
@mock.patch('galaxy_ng.app.metrics_collection.common_data.system_id')
@mock.patch('galaxy_ng.app.metrics_collection.common_data.hub_version')
def test_config(mock_hub_version, mock_system_id):
    mock_system_id.return_value = 'test_id'
    mock_hub_version.return_value = '1.2.3'
    config = common_data.config()
    assert config['install_uuid'] == 'test_id'
    assert config['hub_version'] == '1.2.3'


@mock.patch('galaxy_ng.app.metrics_collection.common_data.api_status')
def test_instance_info(mock_api_status):
    mock_api_status.return_value = {'online_workers': ['worker1']}
    info = common_data.instance_info()
    assert info['online_workers'] == ['worker1']
