from unittest import mock

from galaxy_ng.app.metrics_collection.automation_analytics import data


@mock.patch('galaxy_ng.app.metrics_collection.automation_analytics.data.connection')
@mock.patch('galaxy_ng.app.metrics_collection.automation_analytics.data._get_csv_splitter')
def test_export_to_csv(mock_get_csv_splitter, mock_connection):
    mock_splitter = mock.Mock()
    mock_get_csv_splitter.return_value = mock_splitter
    mock_cursor = mock.Mock()
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    mock_copy = mock.Mock()
    mock_cursor.copy.return_value.__enter__.return_value = mock_copy
    mock_copy.read.side_effect = [b'test_data', None]

    query = "SELECT 1"
    data.export_to_csv('/tmp', 'test_file', query)

    mock_cursor.copy.assert_called_once_with(
        'COPY (\n    SELECT 1\n    ) TO STDOUT WITH CSV HEADER\n    '
    )
    mock_splitter.write.assert_called_once_with('test_data')
    mock_splitter.file_list.assert_called_once()
