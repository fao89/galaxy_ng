from unittest import mock
from django.test import TestCase
import uuid

from galaxy_ng.app.utils import galaxy


def test_generate_unverified_email():
    email = galaxy.generate_unverified_email('12345')
    assert email == '12345@GALAXY.GITHUB.UNVERIFIED.COM'


def test_uuid_conversion():
    u = uuid.uuid4()
    i = galaxy.uuid_to_int(str(u))
    u2 = galaxy.int_to_uuid(i)
    assert str(u) == u2


@mock.patch('time.sleep')
@mock.patch('requests.get')
def test_safe_fetch(mock_get, mock_sleep):
    mock_response_500 = mock.Mock()
    mock_response_500.status_code = 500
    mock_response_200 = mock.Mock()
    mock_response_200.status_code = 200
    mock_get.side_effect = [mock_response_500, mock_response_200]

    response = galaxy.safe_fetch('http://test.com')
    assert response.status_code == 200
    mock_sleep.assert_called_once_with(60)


@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_paginated_results(mock_safe_fetch):
    mock_response1 = mock.Mock()
    mock_response1.json.return_value = {
        'results': [1, 2, 3],
        'next_link': '/api/v1/next'
    }
    mock_response2 = mock.Mock()
    mock_response2.json.return_value = {
        'results': [4, 5, 6],
        'next_link': None
    }
    mock_safe_fetch.side_effect = [mock_response1, mock_response2]

    results = galaxy.paginated_results('http://test.com/api/v1/start')
    assert results == [1, 2, 3, 4, 5, 6]


@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_find_namespace(mock_safe_fetch):
    mock_ns_response = mock.Mock()
    mock_ns_response.json.return_value = {
        'results': [{'name': 'test_ns', 'id': 1}]
    }
    mock_owners_response = mock.Mock()
    mock_owners_response.json.return_value = {
        'results': [{'username': 'test_user'}],
        'next_link': None
    }
    mock_safe_fetch.side_effect = [mock_ns_response, mock_owners_response]

    name, info = galaxy.find_namespace(name='test_ns')
    assert name == 'test_ns'
    assert info['summary_fields']['owners'][0]['username'] == 'test_user'


@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_get_namespace_owners_details(mock_safe_fetch):
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        'results': [{'username': 'test_user'}],
        'next_link': None
    }
    mock_safe_fetch.return_value = mock_response

    owners = galaxy.get_namespace_owners_details('http://test.com', 1)
    assert owners[0]['username'] == 'test_user'


@mock.patch('galaxy_ng.app.utils.galaxy.get_namespace_owners_details')
@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_upstream_namespace_iterator(mock_safe_fetch, mock_get_owners):
    mock_response = mock.Mock()
    mock_response.json.return_value = {
        'count': 1,
        'results': [{'id': 1, 'summary_fields': {'content_counts': {'collection': 1}}}],
        'next_link': None
    }
    mock_safe_fetch.return_value = mock_response
    mock_get_owners.return_value = [{'username': 'test_user'}]

    for total, data in galaxy.upstream_namespace_iterator():
        assert total == 1
        assert data['summary_fields']['owners'][0]['username'] == 'test_user'


@mock.patch('galaxy_ng.app.utils.galaxy.paginated_results')
@mock.patch('galaxy_ng.app.utils.galaxy.get_namespace_owners_details')
@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_upstream_collection_iterator(mock_safe_fetch, mock_get_owners, mock_paginated):
    mock_ns_response = mock.Mock()
    mock_ns_response.json.return_value = {'id': 1, 'summary_fields': {}}
    mock_collection_response = mock.Mock()
    mock_collection_response.json.return_value = {
        'results': [{'namespace': {'id': 1}, 'versions_url': 'http://versions'}],
        'next_link': None
    }
    mock_safe_fetch.side_effect = [mock_collection_response, mock_ns_response]
    mock_get_owners.return_value = [{'username': 'test_user'}]
    mock_paginated.return_value = [{'version': '1.0.0'}]

    for ns, coll, versions in galaxy.upstream_collection_iterator():
        assert ns['summary_fields']['owners'][0]['username'] == 'test_user'
        assert versions[0]['version'] == '1.0.0'


@mock.patch('galaxy_ng.app.utils.galaxy.paginated_results')
@mock.patch('galaxy_ng.app.utils.galaxy.get_namespace_owners_details')
@mock.patch('galaxy_ng.app.utils.galaxy.safe_fetch')
def test_upstream_role_iterator(mock_safe_fetch, mock_get_owners, mock_paginated):
    mock_role_list_response = mock.Mock()
    mock_role_list_response.json.return_value = {
        'results': [{'id': 1}],
        'next_link': None
    }
    mock_role_response = mock.Mock()
    mock_role_response.json.return_value = {'summary_fields': {'namespace': {'id': 1}}}
    mock_ns_response = mock.Mock()
    mock_ns_response.json.return_value = {'id': 1, 'summary_fields': {}}
    mock_safe_fetch.side_effect = [
        mock_role_list_response,
        mock_role_response,
        mock_ns_response
    ]
    mock_get_owners.return_value = [{'username': 'test_user'}]
    mock_paginated.return_value = [{'version': '1.0.0'}]

    for ns, role, versions in galaxy.upstream_role_iterator():
        assert ns['summary_fields']['owners'][0]['username'] == 'test_user'
        assert versions[0]['version'] == '1.0.0'


class TestGalaxyUtils(TestCase):
    def test_upstream_role_iterator_with_user(self):
        roles = []
        for _namespace, role, _versions in galaxy.upstream_role_iterator(github_user="jctanner"):
            roles.append(role)
        assert sorted({x["github_user"] for x in roles}) == ["jctanner"]

    def test_upstream_role_iterator_with_user_and_name(self):
        roles = []
        iterator_kwargs = {"github_user": "geerlingguy", "role_name": "docker"}
        for _namespace, role, _versions in galaxy.upstream_role_iterator(**iterator_kwargs):
            roles.append(role)
        assert len(roles) == 1
        assert roles[0]["github_user"] == "geerlingguy"
        assert roles[0]["name"] == "docker"

    def test_upstream_role_iterator_with_limit(self):
        limit = 10
        count = 0
        for _namespace, _role, _versions in galaxy.upstream_role_iterator(limit=limit):
            count += 1
        assert count == limit


class UUIDConversionTestCase(TestCase):
    def test_uuid_to_int_and_back(self):
        """Make sure uuids can become ints and then back to uuids"""
        for _i in range(1000):
            test_uuid = str(uuid.uuid4())
            test_int = galaxy.uuid_to_int(test_uuid)
            reversed_uuid = galaxy.int_to_uuid(test_int)
            assert test_uuid == reversed_uuid, f"{test_uuid} != {reversed_uuid}"
