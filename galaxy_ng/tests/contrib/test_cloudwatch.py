
from unittest import mock

from django.test import override_settings

from galaxy_ng.contrib import cloudwatch


@override_settings(
    CLOUDWATCH_ACCESS_KEY_ID='test_id',
    CLOUDWATCH_SECRET_ACCESS_KEY='test_key',
    CLOUDWATCH_REGION_NAME='test_region',
    CLOUDWATCH_LOGGING_GROUP='test_group',
    CLOUDWATCH_LOGGING_STREAM_NAME='test_stream'
)
@mock.patch('boto3.client')
def test_cloudwatch_handler(mock_boto3_client):
    handler = cloudwatch.CloudWatchHandler()

    mock_boto3_client.assert_called_once_with(
        'logs',
        aws_access_key_id='test_id',
        aws_secret_access_key='test_key',
        region_name='test_region'
    )

    assert handler.log_group_name == 'test_group'
    assert handler.log_stream_name == 'test_stream'
