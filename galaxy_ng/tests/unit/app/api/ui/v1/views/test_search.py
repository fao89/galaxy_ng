
from unittest import mock

from django.test import RequestFactory
from rest_framework.exceptions import ValidationError

from galaxy_ng.app.api.ui.v1.views import search


def test_get_filter_params():
    factory = RequestFactory()
    request = factory.get('/?keywords=test&type=collection&tags=tag1&tags=tag2')
    view = search.SearchListView()
    view.request = request
    params = view.get_filter_params(request)
    assert params == {
        'keywords': 'test',
        'type': 'collection',
        'tags': ['tag1', 'tag2']
    }


def test_get_sorting_param():
    factory = RequestFactory()
    request = factory.get('/?order_by=-name')
    view = search.SearchListView()
    view.request = request
    sort = view.get_sorting_param(request)
    assert sort == ['-name']


def test_get_sorting_param_invalid():
    factory = RequestFactory()
    request = factory.get('/?order_by=invalid_field')
    view = search.SearchListView()
    view.request = request
    with ValidationError as e:
        view.get_sorting_param(request)
        assert 'invalid_field' in str(e)


@mock.patch('galaxy_ng.app.api.ui.v1.views.search.CollectionVersion')
def test_get_collection_queryset(mock_collection_version):
    view = search.SearchListView()
    view.get_collection_queryset()
    mock_collection_version.objects.annotate.assert_called_once()


@mock.patch('galaxy_ng.app.api.ui.v1.views.search.LegacyRole')
def test_get_role_queryset(mock_legacy_role):
    view = search.SearchListView()
    view.get_role_queryset()
    mock_legacy_role.objects.annotate.assert_called_once()


def test_filter_and_sort():
    mock_collections = mock.Mock()
    mock_roles = mock.Mock()
    view = search.SearchListView()
    view.filter_and_sort(mock_collections, mock_roles, {}, ['-name'])
    mock_collections.union.assert_called_once_with(mock_roles, all=True)
    mock_collections.union.return_value.order_by.assert_called_once_with('-name')
